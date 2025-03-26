import os
os.environ["NEST_ASYNCIO"] = "0"
import json
import secrets
import datetime
from random import SystemRandom
from datetime import datetime
from bitrecs.protocol import BitrecsRequest
safe_random = SystemRandom()
from dataclasses import asdict, dataclass
from typing import List, Optional, Set
from bitrecs.commerce.product import CatalogProvider, Product, ProductFactory
from bitrecs.llms.factory import LLM, LLMFactory
from bitrecs.llms.prompt_factory import PromptFactory
from dotenv import load_dotenv
load_dotenv()


LOCAL_OLLAMA_URL = "http://10.0.0.40:11434/api/chat"
OLLAMA_MODEL = "mistral-nemo"

#MODEL_BATTERY = ["mistral-nemo", "phi4", "qwen2.5:14b"]
MODEL_BATTERY = ["mistral-nemo", "llama3.1", "phi4", "gemma3:12b", "qwen2.5:14b"]
#MODEL_BATTERY = ["llama3.1:70b", "qwen2.5:32b", "gemma3:27b", "nemotron:latest"]


@dataclass
class TestConfig:
    similarity_threshold: float = 0.33
    top_n: int = 2
    num_recs: int = 6
    real_set_count: int = len(MODEL_BATTERY)
    fake_set_count: int = 9


def product_woo():
    woo_catalog = "./tests/data/woocommerce/product_catalog.csv" #2038 records
    catalog = ProductFactory.tryload_catalog_to_json(CatalogProvider.WOOCOMMERCE, woo_catalog)
    products = ProductFactory.convert(catalog, CatalogProvider.WOOCOMMERCE)
    return products

def product_shopify():
    shopify_catalog = "./tests/data/shopify/electronics/shopify_products.csv"
    catalog = ProductFactory.tryload_catalog_to_json(CatalogProvider.SHOPIFY, shopify_catalog)
    products = ProductFactory.convert(catalog, CatalogProvider.SHOPIFY)
    return products

def product_1k():
    with open("./tests/data/amazon/office/amazon_office_sample_1000.json", "r") as f:
        data = f.read()
    products = ProductFactory.convert(data, CatalogProvider.AMAZON)
    return products

def product_5k():
    with open("./tests/data/amazon/office/amazon_office_sample_5000.json", "r") as f:
        data = f.read()    
    products = ProductFactory.convert(data, CatalogProvider.AMAZON)
    return products

def product_20k():    
    with open("./tests/data/amazon/office/amazon_office_sample_20000.json", "r") as f:
        data = f.read()    
    products = ProductFactory.convert(data, CatalogProvider.AMAZON)
    return products

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
    
    # Calculate average distance for each set to all others
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

def select_most_similar_sets_from_bitrecs2(rec_sets: List[BitrecsRequest], top_n: int = 2) -> List[BitrecsRequest]:
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
        
    # Convert results to sets of SKUs
    sku_sets = [set(r['sku'] for r in req.results) for req in rec_sets]
    
    # Get indices of most similar sets
    sim = select_most_similar_sets(sku_sets, top_n)
    
    # Return the corresponding BitrecsRequest objects
    return [rec_sets[i] for i in sim]

def select_most_similar_sets_from_bitrecs3(rec_sets: List[BitrecsRequest], top_n: int = 2, 
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

def select_most_similar_sets_from_bitrecs4(
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


def get_rec(products, sku, model=None, num_recs=5) -> list:
    if not sku:
        raise ValueError("sku is required")
    
    #products = product_5k()
    products = ProductFactory.dedupe(products)
    user_prompt = sku    
    debug_prompts = False
    match = [products for products in products if products.sku == user_prompt][0]
    print(match)

    context = json.dumps([asdict(products) for products in products])
    factory = PromptFactory(sku=user_prompt, 
                            context=context, 
                            num_recs=num_recs, 
                            load_catalog=False, 
                            debug=debug_prompts)
    
    prompt = factory.generate_prompt()    
    if not model:
        model = safe_random.choice(MODEL_BATTERY)
    print(f"Model:\033[32m {model} \033[0m")

    llm_response = LLMFactory.query_llm(server=LLM.OLLAMA_LOCAL,
                                 model=model, 
                                 system_prompt="You are a helpful assistant", 
                                 temp=0.0, user_prompt=prompt)    
    parsed_recs = PromptFactory.tryparse_llm(llm_response) 
    assert len(parsed_recs) == num_recs
    return parsed_recs


def get_rec_fake(sku, num_recs=5) -> list:
    if not sku:
        raise ValueError("sku is required")
    products = product_1k()
    products = ProductFactory.dedupe(products)
    result = safe_random.sample(products, num_recs)
    return result


def mock_br_request(products: List[Product], group_id: str, sku: str, model: str, num_recs: int) -> Optional[BitrecsRequest]:
    assert num_recs > 0 and num_recs <= 20
    #products = ProductFactory.dedupe(product_20k())
    
    user_prompt = sku    
    debug_prompts = False
    match = [products for products in products if products.sku == user_prompt][0]
    print(match)

    context = json.dumps([asdict(products) for products in products])
    factory = PromptFactory(sku=user_prompt, 
                            context=context, 
                            num_recs=num_recs, 
                            load_catalog=False, 
                            debug=debug_prompts)
    
    prompt = factory.generate_prompt()    
    if not model:
        model = safe_random.choice(MODEL_BATTERY)
    print(f"Model:\033[32m {model} \033[0m")

    llm_response = LLMFactory.query_llm(server=LLM.OLLAMA_LOCAL,
                                 model=model, 
                                 system_prompt="You are a helpful assistant", 
                                 temp=0.0, user_prompt=prompt)    
    parsed_recs = PromptFactory.tryparse_llm(llm_response) 
    assert len(parsed_recs) == num_recs

    m = BitrecsRequest(
        created_at=datetime.now().isoformat(),
        user="test_user",
        num_results=num_recs,
        query=sku,
        context="[]",
        site_key=group_id,
        results=parsed_recs,
        models_used=[model],
        miner_uid=str(safe_random.randint(10, 1000)),
        miner_hotkey=secrets.token_hex(16)
    )
    return m


def recommender_presenter2(original_sku: str, recs: List[Set[str]]) -> str:    
    result = f"Target SKU: \033[32m {original_sku} \033[0m\n"
    target_product_name = product_name_by_sku_trimmed(original_sku, 200)
    result += f"Target Product:\033[32m{target_product_name} \033[0m\n"
    result += "------------------------------------------------------------\n"
    seen_names = set()
    for i, rec_set in enumerate(recs):
        for rec in rec_set:        
            name = product_name_by_sku_trimmed(rec, 90)
            if name in seen_names:
                result += f"\033[32m{rec} - {name}\033[0m\n"
                continue
            seen_names.add(name)
            result += f"{rec} - {name}\n"
    return result


def recommender_presenter(original_sku: str, recs: List[Set[str]]) -> str:    
    result = f"Target SKU: \033[32m {original_sku} \033[0m\n"
    target_product_name = product_name_by_sku_trimmed(original_sku, 200)
    result += f"Target Product:\033[32m{target_product_name} \033[0m\n"
    result += "------------------------------------------------------------\n"
    
    # Track matches with simple counter
    matches = {}  # name -> count
    
    # First pass - count matches
    for rec_set in recs:
        for rec in rec_set:
            name = product_name_by_sku_trimmed(rec, 90)
            matches[name] = matches.get(name, 0) + 1
    
    # Second pass - output with emphasis on matches
    seen = set()
    for rec_set in recs:
        for rec in rec_set:
            name = product_name_by_sku_trimmed(rec, 90)
            if (rec, name) in seen:
                continue
                
            seen.add((rec, name))
            count = matches[name]
            if count > 1:
                # Double match - bright green
                result += f"\033[1;32m{rec} - {name} (!)\033[0m\n"
            elif count == 1:
                # Single appearance - normal
                result += f"{rec} - {name}\n"

    result += "\n"
    return result


def product_name_by_sku_trimmed(sku: str, take_length: int = 50, products = None) -> str:
    try:
        if not products:
            products = product_20k()
        #products = ProductFactory.dedupe(products)
        selected_product = [p for p in products if p.sku == sku][0]
        name = selected_product.name
        if len(name) > take_length:
            name = name[:take_length] + "..."
        return name
        
    except Exception as e:
        print(e)
        return f"Error loading sku {sku}"
    



def test_warmup():
    prompt = "Tell me a joke"
    model = OLLAMA_MODEL
    llm_response = LLMFactory.query_llm(server=LLM.OLLAMA_LOCAL,
                                 model=model, 
                                 system_prompt="You are a helpful assistant", 
                                 temp=0.0, user_prompt=prompt)
    print(llm_response)
    assert llm_response is not None


def test_all_sets_matryoshka():
    list1 = product_1k()
    list2 = product_5k()
    list3 = product_20k()    
    set1 = set(item.sku for item in list1)
    set2 = set(item.sku for item in list2)
    set3 = set(item.sku for item in list3)
    assert set1.issubset(set2)
    assert set2.issubset(set3)
    assert (set1 & set2).issubset(set3)


def test_local_llm_bitrecs_mock_ok():
    group_id = secrets.token_hex(16)
    products = product_1k()
    sku = safe_random.choice(products).sku
    print(f"Group ID: {group_id}")
    print(f"SKU: {sku}")
    
    mock_request = mock_br_request(products, group_id, sku, "mistral-nemo", 5)
    assert mock_request is not None
    assert mock_request.num_results == 5
    assert mock_request.query == sku
    assert mock_request.results is not None
    assert len(mock_request.results) == 5
    assert mock_request.models_used is not None
    assert len(mock_request.models_used) == 1
    assert mock_request.miner_uid is not None
    assert mock_request.miner_hotkey is not None



def test_local_llm_base_config_jaccard():
    config = TestConfig()    
    #products = product_1k()
    products = product_5k()
    products = ProductFactory.dedupe(products)
    product = safe_random.choice(products)
    
    print("\n=== Recommendation Set Analysis ===")
    print(f"Testing recommendations for product SKU: {product.sku}")
        
    rec_sets = []
    model_recs = {}
    models_used = []
    
    print(f"Number of recommendations: {config.num_recs}")
    print(f"Number of real sets: {config.real_set_count}")
    print(f"Number of fake sets: {config.fake_set_count}")    
    
    print("\nGenerating real recommendations...")
    for i in range(config.real_set_count):
        this_model = MODEL_BATTERY[i % len(MODEL_BATTERY)]
        recs = get_rec(products, product.sku, this_model, config.num_recs)
        assert recs is not None
        rec_set = set(str(r['sku']) for r in recs)
        rec_sets.append(rec_set)
        print(f"Set {i} (Real) {this_model}: {sorted(list(rec_set))}")
        model_recs[this_model] = recs
        models_used.append(this_model)
        
    print("\nGenerating random recommendations...")
    for i in range(config.fake_set_count):
        this_model = f"random-{i}"
        fake_recs = get_rec_fake(product.sku, config.num_recs)
        assert fake_recs is not None
        fake_set = set(str(r.sku) for r in fake_recs)
        rec_sets.append(fake_set)
        print(f"Set {i} (Random) {this_model}: {sorted(list(fake_set))}")        
        model_recs[this_model] = recs
        models_used.append(this_model)
   
    print("\nJaccard Distance Matrix:")
    print("=" * 60)    
    
    header = "Sets:"
    for i in range(len(rec_sets)):
        header += f"{i:>7}"
    print(header)
    print("-" * 60)
    
    print(f"total of {len(rec_sets)} sets")
    
    # Calculate Jaccard distances between all pairs with aligned columns
    for i in range(len(rec_sets)):
        row = f"{i:4d}"
        for j in range(len(rec_sets)):
            if j < i:
                distance = calculate_jaccard_distance(rec_sets[i], rec_sets[j])
                row += f"{distance:7.3f}"
            else:
                row += "      -"
        print(row)
    
    print("\nNote: Lower distances between sets (real) vs (random)")
    print("      indicate better recommendation quality")
    print("=" * 40)

    # Verify all distances are valid
    for i in range(len(rec_sets)):
        for j in range(i + 1, len(rec_sets)):
            distance = calculate_jaccard_distance(rec_sets[i], rec_sets[j])
            assert 0 <= distance <= 1

    print("\nSelecting most similar sets:")
    most_similar = select_most_similar_sets(rec_sets, top_n=config.top_n)
    print(f"Most similar set indices: {most_similar}")
    print("Selected sets:")
    for idx in most_similar:
        model_used = models_used[idx]
        print(f"Set {idx}: {sorted(list(rec_sets[idx]))} - \033[32m {model_used} \033[0m")

    # Verify that the most similar sets are the real ones
    for idx in most_similar:
        assert idx <= config.real_set_count

    
    print("\nVerifying recommendation quality:")
    print("=" * 60)
    
    # Check that all selected sets are from real recommendations
    for idx in most_similar:
        if idx >= config.real_set_count:
            print(f"WARNING: Set {idx} is a random set, not a real recommendation!")
        assert idx < config.real_set_count, f"Set {idx} is not from real recommendations (idx >= {config.real_set_count})"
    
    similar_set_distances = []
    for i in range(len(most_similar)):
        for j in range(i + 1, len(most_similar)):
            dist = calculate_jaccard_distance(rec_sets[most_similar[i]], rec_sets[most_similar[j]])
            similar_set_distances.append(dist)
    
    avg_similarity = 1 - (sum(similar_set_distances) / len(similar_set_distances))
    print(f"Average similarity between selected sets: {avg_similarity:.3f}")
    print(f"Average distance between selected sets: {1-avg_similarity:.3f}")    
    
    assert avg_similarity >= config.similarity_threshold, \
        f"Selected sets have low similarity ({avg_similarity:.3f} < {config.similarity_threshold})"
    
    print("\nQuality check passed:")
    print(f"✓ All selected sets are from real recommendations")
    print(f"✓ Average similarity above threshold ({avg_similarity:.3f} >= {config.similarity_threshold})")
    print("=" * 60)

    summary = recommender_presenter(product.sku, [rec_sets[idx] for idx in most_similar])
    print(summary)



def test_local_llm_raw_1k_jaccard():
    """Test recommendation sets using Jaccard similarity with model tracking"""
    group_id = secrets.token_hex(16)
    products = product_1k()
    products = ProductFactory.dedupe(products)
    selected_product = safe_random.choice(products)
    sku = selected_product.sku
    
    config = TestConfig()
    rec_tracking : List[Set] = []
    
    print(f"\n=== Recommendation Analysis ===")
    print(f"SKU: {sku}")
    print(f"Recommendations per set: {config.num_recs}")    
    
    print("\nGenerating random recommendations...")
    for i in range(config.fake_set_count):
        model_name = f"random-{i}"
        fake_recs = get_rec_fake(sku, config.num_recs)
        fake_set = set(str(r.sku) for r in fake_recs)
        rec_tracking.append((fake_set, model_name))
        print(f"Set (Random) {model_name}: {sorted(list(fake_set))}")    
    
    print("\nGenerating model recommendations...")
    #battery = MODEL_BATTERY[:2]
    battery = MODEL_BATTERY    
    safe_random.shuffle(battery)

    for model in battery:
        mock_req = mock_br_request(products, group_id, sku, model, config.num_recs)
        rec_set = set(str(r['sku']) for r in mock_req.results)
        rec_tracking.append((rec_set, model))
        print(f"Set {model}: {sorted(list(rec_set))}")

    
    rec_sets = [item[0] for item in rec_tracking]        
    print("\nJaccard Distance Matrix:")
    print("=" * 60)
    most_similar = select_most_similar_sets(rec_sets, top_n=config.top_n)
    assert most_similar is not None
    assert len(most_similar) == config.top_n
    
    print("\nMost Similar Sets:")
    print("-" * 60)
    for idx in most_similar:
        rec_set, model = rec_tracking[idx]
        print(f"Set {idx} ({model}):")
        print(f"  SKUs: {sorted(list(rec_set))}")        
    
    for idx in most_similar:
        model = rec_tracking[idx][1]
        is_random = model.startswith("random-")
        assert not is_random, f"Selected set {idx} is random, expected real model"
    


def test_local_llm_bitrecs_5k_jaccard():
    group_id = secrets.token_hex(16)
    #products = product_1k()
    products = product_5k()
    products = ProductFactory.dedupe(products)
    sku = safe_random.choice(products).sku
    print(f"Group ID: {group_id}")
    print(f"SKU: {sku}")
    product_name = product_name_by_sku_trimmed(sku, 500)
    print(f"Target Product:\033[32m{product_name} \033[0m")

    config = TestConfig()
    rec_sets = []
    models_used = []
        
    #battery = MODEL_BATTERY[:3]
    battery = MODEL_BATTERY    
    safe_random.shuffle(battery)

    print(f"USING LOCAL MODEL BATTERY of size: {len(battery)}")
    print(f"Number of recommendations: {config.num_recs}")
    print(f"Number of real sets: {len(battery)}")
    print(f"Number of fake sets: {config.fake_set_count}")  
    print(f"Top N: {config.top_n}")
    
    for i, thing in enumerate(range(config.fake_set_count)):
        this_model = f"random-{i}"
        fake_recs = get_rec_fake(sku, config.num_recs)
        assert fake_recs is not None
        fake_set = set(str(r.sku) for r in fake_recs)
        assert len(fake_set) == config.num_recs
        print(f"Set {i} (Random) {this_model}: {sorted(list(fake_set))}")
        rec_sets.append(fake_set)
        models_used.append(this_model)
     
    for model in battery:
        mock_req = mock_br_request(products, group_id, sku, model, config.num_recs)
        assert mock_req is not None        
        rec_set = set(str(r['sku']) for r in mock_req.results)        
        rec_sets.append(rec_set)
        i += 1
        print(f"Set {i} {model}: {sorted(list(rec_set))}")
        models_used.append(model)     
        
    print("\nFinished generating rec sets")  
    most_similar = select_most_similar_sets(rec_sets, top_n=config.top_n)
    assert most_similar is not None
    assert len(most_similar) == config.top_n

    print(f"\nMost similar set indices: {most_similar}")
    print("Selected sets:")
    for idx in most_similar:
        print(f"Set {idx}/{len(rec_sets)} {sorted(list(rec_sets[idx]))}")
        model = models_used[idx]
        print(f"Model: {model}")

    report = recommender_presenter(sku, [rec_sets[idx] for idx in most_similar])
    print(report)       


def test_local_llm_bitrecs_protocol_5k_jaccard():
    """Test recommendation sets using BitrecsRequest protocol"""
    group_id = secrets.token_hex(16)
    #products = product_1k()
    products = product_5k()
    products = ProductFactory.dedupe(products)
    selected_product = safe_random.choice(products)
    sku = selected_product.sku
    
    config = TestConfig()
    rec_requests = []  # List of BitrecsRequest objects
    
    print(f"\n=== Protocol Recommendation Analysis ===")
    print(f"Original Product:")
    print(f"SKU: \033[32m {sku} \033[0m")
    print(f"Name: \033[32m {selected_product.name} \033[0m")
    print(f"Price: ${selected_product.price}")
    
    # Generate fake recommendations first
    print("\nGenerating random recommendations...")
    for i in range(config.fake_set_count):
        fake_recs = get_rec_fake(sku, config.num_recs)
        req = BitrecsRequest(
            created_at=datetime.now().isoformat(),
            user="test_user",
            num_results=config.num_recs,
            query=sku,
            context="[]",
            site_key=group_id,
            results=[{"sku": r.sku} for r in fake_recs],
            models_used=[f"random-{i}"],
            miner_uid=str(safe_random.randint(10, 100)),
            miner_hotkey=secrets.token_hex(16)
        )
        rec_requests.append(req)
        print(f"Set random-{i}: {[r['sku'] for r in req.results]}")
    
    # Generate real recommendations
    print("\nGenerating model recommendations...")
    battery = MODEL_BATTERY[:2]  # Using first 2 models
    for model in battery:
        req = mock_br_request(products, group_id, sku, model, config.num_recs)
        rec_requests.append(req)
        print(f"Set {model}: {[r['sku'] for r in req.results]}")


    # No threshold
    most_similar = select_most_similar_sets_from_bitrecs2(rec_requests, top_n=config.top_n)
    assert most_similar is not None
    assert len(most_similar) == config.top_n

    # 33% with threshold
    low_threshold = 0.10
    most_similar2 = select_most_similar_sets_from_bitrecs3(rec_requests, 
                                                           top_n=config.top_n, 
                                                           similarity_threshold=low_threshold)  

    # 51% or null
    med_threshold = 0.51
    most_similar3 = select_most_similar_sets_from_bitrecs4(rec_requests, 
                                                           top_n=config.top_n, 
                                                           similarity_threshold=med_threshold)
 
    print("\nFinished generating rec sets") 
    print("Selected sets:")
    for req in most_similar:
        model = req.models_used[0]
        skus = [r['sku'] for r in req.results]
        print(f"Model {model}:")
        print(f"  SKUs: {sorted(skus)}")      

    selected_sets = [set(r['sku'] for r in req.results) for req in most_similar]
    report = recommender_presenter(sku, selected_sets)
    print(report)

    if most_similar2:
        print("Selected sets:")
        for req in most_similar2:
            model = req.models_used[0]
            skus = [r['sku'] for r in req.results]
            print(f"Model {model}:")
            print(f"  SKUs: {sorted(skus)}")      
            
        selected_sets2 = [set(r['sku'] for r in req.results) for req in most_similar2]
        report = recommender_presenter(sku, selected_sets2)
        print(f"Threshold {low_threshold}")
        print(report)
    else:
        print(f"No sets found meeting threshold {low_threshold}")

    if most_similar3:
        print("Selected sets:")
        for req in most_similar3:
            model = req.models_used[0]
            skus = [r['sku'] for r in req.results]
            print(f"Model {model}:")
            print(f"  SKUs: {sorted(skus)}")
        selected_sets3 = [set(r['sku'] for r in req.results) for req in most_similar3]
        report = recommender_presenter(sku, selected_sets3)
        print(f"\033[1;32m Threshold {med_threshold} \033[0m")
        print(report)
    else:
        print(f"\033[31m Noo sets found meeting threshold {med_threshold} \033[0m")

  
