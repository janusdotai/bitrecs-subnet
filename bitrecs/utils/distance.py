import json
from enum import Enum
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


def select_most_similar_sets(rec_sets: List[Set], top_n: int = 2) -> List[int]:
    """
    Select most similar sets based on Jaccard similarity.
    Returns indices of the top N most similar pairs.
    
    Args:
        rec_sets: List of sets to compare
        top_n: Number of indices to return (default 2)
    Returns:
        List of indices for the most similar sets
    """
    n = len(rec_sets)
    all_pairs = []
    
    # Calculate similarities for all pairs
    for i in range(n):
        for j in range(i + 1, n):
            distance = calculate_jaccard_distance(rec_sets[i], rec_sets[j])
            similarity = 1 - distance
            all_pairs.append((similarity, i, j))
    
    # Sort by similarity (highest first)
    all_pairs.sort(reverse=True)
    
    # Debug info
    print("\nTop similarity pairs:")
    for sim, i, j in all_pairs[:5]:
        print(f"Sets {i},{j}: similarity={sim:.3f} (distance={1-sim:.3f})")
    
    # Get indices from top pairs
    selected = set()
    result = []
    
    # Take indices from best pairs until we have top_n
    for sim, i, j in all_pairs:
        for idx in (i, j):
            if idx not in selected and len(result) < top_n:
                selected.add(idx)
                result.append(idx)
        if len(result) >= top_n:
            break
            
    return result[:top_n]


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





class ColorScheme(Enum):
    VIRIDIS = "viridis"
    ROCKET = "rocket"
    MAKOTO = "makoto"
    SPECTRAL = "spectral"

class ColorPalette:
    """Color schemes for matrix visualization"""
    SCHEMES = {
        ColorScheme.VIRIDIS: {
            "strong": "\033[38;5;114m",  # Lime Green
            "medium": "\033[38;5;37m",     # Teal
            "weak": "\033[38;5;31m",   # Deep Blue
            "minimal": "\033[38;5;55m",   # Dark Purple 
            "highlight": "\033[38;5;227m" # Bright Yellow
        },
        ColorScheme.ROCKET: {
            "strong": "\033[38;5;89m",    # Deep Plum
            "medium": "\033[38;5;161m",   # Reddish Purple
            "weak": "\033[38;5;196m",     # Warm Red
            "minimal": "\033[38;5;209m",   # Coral
            "highlight": "\033[38;5;223m"  # Light Peach
        },
        ColorScheme.MAKOTO: {
            "strong": "\033[38;5;232m",   # Near Black
            "medium": "\033[38;5;24m",    # Dark Blue
            "weak": "\033[38;5;67m",      # Steel Blue
            "minimal": "\033[38;5;117m",  # Light Sky Blue
            "highlight": "\033[38;5;195m" # Pale Blue
        },
        ColorScheme.SPECTRAL: {
            "strong": "\033[38;5;160m",   # Red
            "medium": "\033[38;5;215m",   # Orange
            "weak": "\033[38;5;229m",     # Soft Yellow
            "minimal": "\033[38;5;151m",  # Mint Green
            "highlight": "\033[38;5;32m"  # Cool Blue
        }
    }

# def display_rec_matrix(
#     rec_sets: List[Set[str]], 
#     models_used: List[str], 
#     highlight_indices: List[int] = None,
#     color_scheme: ColorScheme = ColorScheme.VIRIDIS
# ) -> None:
    
#     matrix = display_rec_matrix_str(
#         rec_sets,
#         models_used,
#         highlight_indices,
#         color_scheme
#     )
#     print(matrix)    


def display_rec_matrix_str(
    rec_sets: List[Set[str]], 
    models_used: List[str], 
    highlight_indices: List[int] = None,
    color_scheme: ColorScheme = ColorScheme.VIRIDIS
) -> str:
    """
    Generate similarity matrix report as a string with customizable color schemes
    
    Args:
        rec_sets: List of recommendation sets
        models_used: List of model names
        highlight_indices: Indices of sets to highlight
        color_scheme: Color scheme to use for visualization
    Returns:
        str: Complete formatted matrix report
    """
    output = []
    colors = ColorPalette.SCHEMES[color_scheme]
    
    output.append(f"\nDistance Matrix - {len(rec_sets)} sets\n")
    
    # Generate header with highlighting
    header = "       "
    for j in range(len(rec_sets)):
        col_num = f"{j:7d}"
        if highlight_indices and j in highlight_indices:
            header += f"{colors['highlight']}{col_num}\033[0m"
        else:
            header += col_num
    output.append(header)
    
    # Track matches for summary
    match_info = []
    
    # Generate matrix with color scheme
    for i in range(len(rec_sets)):
        if highlight_indices and i in highlight_indices:
            row_start = f"{colors['highlight']}{i:4d}  \033[0m"
        else:
            row_start = f"{i:4d}  "
        
        row = []
        for j in range(len(rec_sets)):
            if j < i:
                distance = calculate_jaccard_distance(rec_sets[i], rec_sets[j])
                cell = f"{distance:7.3f}"
                
                if distance < 0.91:
                    match_info.append((i, j, distance, models_used[i], models_used[j]))
                
                if distance < 1.0:
                    if highlight_indices and i in highlight_indices and j in highlight_indices:
                        cell = f"{colors['highlight']}{cell}\033[0m"
                    elif distance <= 0.5:
                        cell = f"{colors['strong']}{cell}\033[0m"
                    elif distance <= 0.7:
                        cell = f"{colors['medium']}{cell}\033[0m"
                    elif distance <= 0.9:
                        cell = f"{colors['weak']}{cell}\033[0m"
                    else:
                        cell = f"{colors['minimal']}{cell}\033[0m"
                row.append(cell)
            else:
                row.append("      -")
        
        output.append(row_start + "".join(row))
    
    # Add match summary with same color scheme
    if match_info:
        output.append("\nSignificant Model Matches (Sorted by Similarity):")
        output.append("-" * 60)
        for i, j, dist, model1, model2 in sorted(match_info, key=lambda x: (1 - x[2]), reverse=True):
            similarity = 1 - dist
            if similarity >= 0.1:
                if similarity >= 0.5:
                    color = colors['strong']
                elif similarity >= 0.3:
                    color = colors['medium']
                elif similarity >= 0.1:
                    color = colors['weak']
                
                output.append(f"{color}Similarity: {similarity:.2f}\033[0m")
                output.append(f"  Model {i}: {model1}")
                output.append(f"  Model {j}: {model2}")
                output.append(f"  Matrix Distance: {dist:.3f}")
                output.append("-" * 40)
                if "random" in model1 or "random" in model2:
                    output.append(f"\033[33m  ⚠️ Warning: Includes random set!\033[0m")
    
    # Add scheme-specific legend
    output.append(f"\nLegend ({color_scheme.value}):")
    output.append(f"{colors['highlight']}Highlighted Rows/Cols\033[0m: Selected sets")
    output.append(f"{colors['strong']}>= 0.5\033[0m "
                 f"{colors['medium']}>= 0.3\033[0m "
                 f"{colors['weak']}>= 0.1\033[0m "
                 f"{colors['minimal']}> 0.0\033[0m: Match strength")
    
    output.append("\nNote: Lower distances between sets (real) vs (random)")
    output.append("      indicate better recommendation quality")
    output.append("=" * 40)
    
    return "\n".join(output)