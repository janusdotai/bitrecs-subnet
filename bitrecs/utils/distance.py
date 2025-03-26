from typing import List, Optional, Set
from bitrecs.protocol import BitrecsRequest


def calculate_jaccard_distance(set1: Set, set2: Set) -> float:  
    if not set1 or not set2:
        return 1.0        
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    if union == 0:
        return 1.0        
    similarity = intersection / union
    distance = 1 - similarity
    return distance

def select_most_similar_sets(rec_sets: List[Set[str]], top_n: int = 2) -> List[int]:
    """
    Select the top N most similar sets based on Jaccard distances.
    Returns indices of the most similar sets.
    
    Args:
        rec_sets: List of sets to compare
        top_n: Number of sets to return (default 2)
    Returns:
        List of indices for the most similar sets
    """
    if len(rec_sets) < 2:
        return list(range(len(rec_sets)))
    avg_distances = []
    for i, set1 in enumerate(rec_sets):
        distances = []
        for j, set2 in enumerate(rec_sets):
            if i != j:
                dist = calculate_jaccard_distance(set1, set2)
                distances.append(dist)
        avg_distances.append((i, sum(distances) / len(distances)))
    
    # Sort by average distance (ascending) and get top N
    sorted_sets = sorted(avg_distances, key=lambda x: x[1])
    selected_indices = [idx for idx, _ in sorted_sets[:top_n]]
    
    return selected_indices

def select_most_similar_bitrecs(rec_sets: List[BitrecsRequest], top_n: int = 2) -> List[BitrecsRequest]:
    """
    Select most similar BitrecsRequest objects based on their SKU recommendations.
    
    Args:
        rec_sets: List of BitrecsRequest objects
        top_n: Number of similar sets to return
    Returns:
        List of most similar BitrecsRequest objects
    """
    if len(rec_sets) < 2:
        return rec_sets
    sku_sets = [set(r['sku'] for r in req.results) for req in rec_sets]        
    sim = select_most_similar_sets(sku_sets, top_n)    
    return [rec_sets[i] for i in sim]

def select_most_similar_bitrecs_threshold(rec_sets: List[BitrecsRequest], top_n: int = 2, 
                                          similarity_threshold: float = 0.51) -> List[BitrecsRequest]:
    """
    Self-contained function to select most similar BitrecsRequest objects.
    Includes internal Jaccard calculation and similarity checks.
    
    Args:
        rec_sets: List of BitrecsRequest objects
        top_n: Number of similar sets to return (default 2)
        similarity_threshold: Minimum similarity required (default 0.51)
    Returns:
        List of most similar BitrecsRequest objects meeting threshold
    """
    if len(rec_sets) < 2:
        return rec_sets

    def calc_jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    # Convert BitrecsRequests to sets of SKUs
    sku_sets = []
    for req in rec_sets:
        sku_set = set(r['sku'] for r in req.results)
        sku_sets.append((sku_set, req))  # Keep original request paired with its SKUs

    # Calculate all pairwise similarities
    pairs = []
    for i in range(len(sku_sets)):
        for j in range(i + 1, len(sku_sets)):
            similarity = calc_jaccard_similarity(sku_sets[i][0], sku_sets[j][0])
            if similarity >= similarity_threshold:
                pairs.append((i, j, similarity))

    # Sort pairs by similarity (highest first)
    pairs.sort(key=lambda x: x[2], reverse=True)

    if not pairs:
        print(f"No pairs found meeting threshold {similarity_threshold}")
        return []

    # Select best pairs meeting criteria
    selected = set()
    selected_requests = []
    
    for i, j, sim in pairs:
        # Add both requests from the pair if we haven't hit top_n
        if len(selected_requests) < top_n:
            if i not in selected:
                selected.add(i)
                selected_requests.append(rec_sets[i])
            if len(selected_requests) < top_n and j not in selected:
                selected.add(j)
                selected_requests.append(rec_sets[j])

    # Print similarity analysis
    print(f"\nSimilarity Analysis:")
    print(f"Found {len(selected_requests)} sets meeting threshold {similarity_threshold}")
    for idx, req in enumerate(selected_requests):
        model = req.models_used[0] if req.models_used else "unknown"
        if idx < len(pairs):
            print(f"Set {idx}: Model {model} (similarity: {pairs[idx][2]:.3f})")
        else:
            print(f"Set {idx}: Model {model}")

    return selected_requests[:top_n]

def select_most_similar_bitrecs_threshold2(
    rec_sets: List[BitrecsRequest], 
    top_n: int = 2, 
    similarity_threshold: float = 0.51
) -> Optional[List[BitrecsRequest]]:
    """
    Select most similar BitrecsRequest objects meeting similarity threshold.
    Returns None if no pairs meet threshold.
    
    Args:
        rec_sets: List of BitrecsRequest objects
        top_n: Number of similar sets to return
        similarity_threshold: Minimum similarity required
    Returns:
        List of similar BitrecsRequest objects or None if no matches
    """
    if len(rec_sets) < 2:
        return None
        
    # Calculate similarities between all pairs
    similar_pairs = []
    for i in range(len(rec_sets)):
        set1 = set(r['sku'] for r in rec_sets[i].results)
        for j in range(i + 1, len(rec_sets)):
            set2 = set(r['sku'] for r in rec_sets[j].results)
            
            # Calculate Jaccard similarity
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            similarity = intersection / union if union > 0 else 0.0
            
            if similarity >= similarity_threshold:
                similar_pairs.append((i, j, similarity))
    
    if not similar_pairs:
        print(f"No pairs found above threshold {similarity_threshold}")
        return None
        
    # Sort by similarity and get best pairs
    similar_pairs.sort(key=lambda x: x[2], reverse=True)
    selected = set()
    result = []
    
    # Take best pairs until we have top_n requests
    for i, j, sim in similar_pairs:
        if len(result) >= top_n:
            break
        if i not in selected:
            selected.add(i)
            result.append(rec_sets[i])
        if len(result) < top_n and j not in selected:
            selected.add(j)
            result.append(rec_sets[j])
            
    return result if result else None
