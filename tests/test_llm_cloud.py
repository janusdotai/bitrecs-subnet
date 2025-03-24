import os
import json
import time
import pytest
from dataclasses import asdict
from random import SystemRandom
safe_random = SystemRandom()
from typing import Counter
from bitrecs.commerce.product import CatalogProvider, Product, ProductFactory
from bitrecs.llms.factory import LLM, LLMFactory
from bitrecs.llms.prompt_factory import PromptFactory
from dotenv import load_dotenv
load_dotenv()

os.environ["NEST_ASYNCIO"] = "0"

LOCAL_OLLAMA_URL = "http://10.0.0.40:11434/api/chat"
OLLAMA_MODEL = "mistral-nemo"

map = [
    {"provider": LLM.OLLAMA_LOCAL, "model": "mistral-nemo"},
    {"provider": LLM.VLLM, "model": "NousResearch/Meta-Llama-3-8B-Instruct"},
    {"provider": LLM.CHAT_GPT, "model": "gpt-4o-mini"},

    #{"provider": LLM.OPEN_ROUTER, "model": "nvidia/llama-3.1-nemotron-70b-instruct"},
    #{"provider": LLM.OPEN_ROUTER, "model": "nousresearch/deephermes-3-llama-3-8b-preview:free"},

    {"provider": LLM.OPEN_ROUTER, "model": "amazon/nova-lite-v1"},    
    #{"provider": LLM.OPEN_ROUTER, "model": "cohere/command-r7b-12-2024"},
    #{"provider": LLM.OPEN_ROUTER, "model": "amazon/nova-micro-v1"},    
    {"provider": LLM.OPEN_ROUTER, "model": "google/gemini-flash-1.5-8b"},
    #{"provider": LLM.OPEN_ROUTER, "model": "google/gemini-2.0-flash-lite-001"},  
    #{"provider": LLM.OPEN_ROUTER, "model": "google/gemini-2.0-flash-001"},  
    
    {"provider": LLM.GROK, "model": "grok-2-latest"},
    {"provider": LLM.GEMINI, "model": "gemini-1.5-flash-8b"},
    {"provider": LLM.CLAUDE, "model": "anthropic/claude-3.5-haiku"}
]

#CLOUD_PROVIDERS = [LLM.OPEN_ROUTER, LLM.GEMINI, LLM.CHAT_GPT, LLM.GROK, LLM.CLAUDE]
CLOUD_PROVIDERS = [LLM.OPEN_ROUTER, LLM.GEMINI, LLM.CHAT_GPT]

#LOCAL_PROVIDERS = [LLM.OLLAMA_LOCAL, LLM.VLLM]
LOCAL_PROVIDERS = [LLM.OLLAMA_LOCAL]


MASTER_SKU = "B08XYRDKDV" 
#HP Envy 6455e Wireless Color All-in-One Printer with 6 Months Free Ink (223R1A) (Renewed Premium)

# 1 failed, 8 passed, 1 skipped, 4 warnings in 147.16s (0:02:27
# 7 passed, 1 skipped, 4 warnings in 35.79s
#7 passed, 4 warnings in 42.26s
#7 passed, 4 warnings in 60.06s (0:01:00)
#2 failed, 6 passed, 4 warnings in 200.12s (0:03:20)

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

def get_local_answer(provider: LLM, prompt: str, model: str, num_recs: int) -> list:
    local_providers = [LLM.OLLAMA_LOCAL, LLM.VLLM]
    if provider not in local_providers:
        raise ValueError("Invalid provider for local call")
    llm_response = LLMFactory.query_llm(server=provider,
                                 model=model, 
                                 system_prompt="You are a helpful assistant", 
                                 temp=0.0, user_prompt=prompt)
    parsed_recs = PromptFactory.tryparse_llm(llm_response)
    return parsed_recs


def test_print_setup():
    print(f"\nMASTER_SKU: {MASTER_SKU}")
    print(f"OLLAMA_MODEL: {OLLAMA_MODEL}")
        
    print(f"\nLOCAL: {LOCAL_PROVIDERS}")
    print(f"CLOUD: {CLOUD_PROVIDERS}")


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


def test_product_dupes():
    list1 = product_1k()
    print(f"loaded {len(list1)} records")
    assert len(list1) == 1000
    d1 = ProductFactory.get_dupe_count(list1)
    print(f"dupe count: {d1}")
    assert d1 == 36
    dd1 = ProductFactory.dedupe(list1)
    print(f"after de-dupe: {len(dd1)} records") 
    assert len(dd1) == (len(list1) - d1)

    list2 = product_5k()
    print(f"loaded {len(list2)} records")
    assert len(list2) == 5000
    d2 = ProductFactory.get_dupe_count(list2)
    print(f"dupe count: {d2}")
    assert d2 == 568
    dd2 = ProductFactory.dedupe(list2)
    print(f"after de-dupe: {len(dd2)} records") 
    assert len(dd2) == (len(list2) - d2)

    list3 = product_20k()
    print(f"loaded {len(list3)} records")
    assert len(list3) == 19_999
    d3 = ProductFactory.get_dupe_count(list3)
    print(f"dupe count: {d3}")
    assert d3 == 4500
    dd3 = ProductFactory.dedupe(list3)
    print(f"after de-dupe: {len(dd3)} records") 
    assert len(dd3) == (len(list3) - d3)


def test_call_local_llm_with_1k_for_baseline():
    products = product_1k() 
    products = ProductFactory.dedupe(products)
    
    user_prompt = MASTER_SKU
    num_recs = 3
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
    #print(prompt)    
    model = OLLAMA_MODEL
    llm_response = LLMFactory.query_llm(server=LLM.OLLAMA_LOCAL,
                                 model=model, 
                                 system_prompt="You are a helpful assistant", 
                                 temp=0.0, user_prompt=prompt)
    parsed_recs = PromptFactory.tryparse_llm(llm_response)   
    print(f"parsed {len(parsed_recs)} records")
    print(parsed_recs)
    
    assert len(parsed_recs) == num_recs
    #check uniques
    skus = [item['sku'] for item in parsed_recs]
    counter = Counter(skus)
    for sku, count in counter.items():
        print(f"{sku}: {count}")
        assert count == 1   
  


def test_call_all_cloud_providers_warmup():    
    #prompt = "Don't be alarmed, we're going to talk about Product Recommendations"
    prompt = f"Tell me a joke today is {safe_random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])}"
    
    count = 0
    for provider in CLOUD_PROVIDERS:

        # if count > 2:
        #     break

        print(f"provider: {provider}")
        model = [m for m in map if m["provider"] == provider][0]["model"]
        print(f"provider: {provider}")
        try:
            print(f"asked: {prompt}")
            llm_response = LLMFactory.query_llm(server=provider,
                                model=model,
                                system_prompt="You are a helpful assistant", 
                                temp=0.0, 
                                user_prompt=prompt)                        
            print(f"response: {llm_response}")                      
            assert llm_response is not None 
            assert len(llm_response) > 0
            print(f"provider: \033[32m {provider} PASSED \033[0m with: {model}")
            count += 1

        except Exception as e:
            print(f"provider: {provider} \033[31m FAILED \033[0m using: {model}")            
            continue            
                     
    assert count == len(CLOUD_PROVIDERS)


#@pytest.mark.skip(reason="skipped")
def test_call_all_cloud_providers_1k_woo_products():    
    raw_products = product_woo()
    products = ProductFactory.dedupe(raw_products)
    print(f"after de-dupe: {len(products)} records")
  
    rp = safe_random.choice(products)
    user_prompt = rp.sku
    #num_recs = 3
    num_recs = safe_random.choice([1, 5, 9, 10, 11, 16, 20])
    debug_prompts = False

    match = [products for products in products if products.sku == user_prompt][0]
    print(match)    
    print(f"num_recs: {num_recs}")

    context = json.dumps([asdict(products) for products in products])
    factory = PromptFactory(sku=user_prompt, 
                            context=context, 
                            num_recs=num_recs, 
                            load_catalog=False, 
                            debug=debug_prompts)
    
    prompt = factory.generate_prompt()
    #print(prompt)
    print(f"prompt length: {len(prompt)}")

    print("********** LOOPING PROVIDERS ")
    success_count = 0
    for provider in CLOUD_PROVIDERS:
        model = [m for m in map if m["provider"] == provider][0]["model"]
        try:   
            st = time.time()         
            llm_response = LLMFactory.query_llm(server=provider,
                                model=model,
                                system_prompt="You are a helpful assistant", 
                                temp=0.0,
                                user_prompt=prompt)
            parsed_recs = PromptFactory.tryparse_llm(llm_response)
            print(f"parsed {len(parsed_recs)} records")
            print(parsed_recs)
            et = time.time()
            diff = et-st
            print(f"provider: \033[32m {provider} run \033[0m {model} : {diff:.2f} seconds")
            assert len(parsed_recs) == num_recs
            #check uniques
            skus = [item['sku'] for item in parsed_recs]
            counter = Counter(skus)
            for sku, count in counter.items():
                print(f"{sku}: {count}")
                assert count == 1

            assert user_prompt not in skus

            success_count += 1
           
            print(f"provider: \033[32m {provider} PASSED woocommerce catalog \033[0m with: {model} in {diff:.2f} seconds")                 
        except Exception as e:
            print(f"provider: {provider} \033[31m FAILED woocommerce catalog \033[0m using: {model}")
            continue

    assert len(CLOUD_PROVIDERS) == success_count
    



@pytest.mark.skip(reason="skipped - stalled")
def test_call_all_cloud_providers_1k_amazon_random():
    raw_products = product_1k()    
    products = ProductFactory.dedupe(raw_products)
    print(f"after de-dupe: {len(products)} records")

    time.sleep(3)
    rp = safe_random.choice(products)
    user_prompt = rp.sku
    #num_recs = 3
    num_recs = safe_random.choice([1, 5, 9, 10, 11, 16, 20])

    debug_prompts = False

    match = [products for products in products if products.sku == user_prompt][0]
    print(match)    
    print(f"num_recs: {num_recs}")

    context = json.dumps([asdict(products) for products in products])
    factory = PromptFactory(sku=user_prompt, 
                            context=context, 
                            num_recs=num_recs, 
                            load_catalog=False, 
                            debug=debug_prompts)
    
    prompt = factory.generate_prompt()
    #print(prompt)
    print(f"prompt length: {len(prompt)}")

    print("********** LOOPING PROVIDERS ")
    success_count = 0
    for provider in CLOUD_PROVIDERS:
        model = [m for m in map if m["provider"] == provider][0]["model"]
        try:            
            llm_response = LLMFactory.query_llm(server=provider,
                                model=model,
                                system_prompt="You are a helpful assistant", 
                                temp=0.0, 
                                user_prompt=prompt)
            parsed_recs = PromptFactory.tryparse_llm(llm_response)
            print(f"parsed {len(parsed_recs)} records")
            print(parsed_recs)

            assert len(parsed_recs) == num_recs

            skus = [item['sku'] for item in parsed_recs]
            counter = Counter(skus)
            for sku, count in counter.items():
                print(f"{sku}: {count}")
                assert count == 1

            assert user_prompt not in sku
            
            success_count += 1
            print(f"provider: \033[32m {provider} PASSED amazon catalog \033[0m with: {model}")
        except Exception as e:
            print(f"provider: {provider} \033[31m FAILED amazon catalog \033[0m using: {model}")            
            continue

    assert len(CLOUD_PROVIDERS) == success_count




#@pytest.mark.skip(reason="skipped - stalled")
def test_call_multiple_open_router_1k_amazon_random():
    raw_products = product_1k()    
    products = ProductFactory.dedupe(raw_products)
    print(f"after de-dupe: {len(products)} records")

    time.sleep(3)
    rp = safe_random.choice(products)
    user_prompt = rp.sku
    #num_recs = 3
    num_recs = safe_random.choice([1, 5, 9, 10, 11, 16, 20])

    debug_prompts = False

    match = [products for products in products if products.sku == user_prompt][0]
    print(match)    
    print(f"num_recs: {num_recs}")

    context = json.dumps([asdict(products) for products in products])
    factory = PromptFactory(sku=user_prompt, 
                            context=context, 
                            num_recs=num_recs, 
                            load_catalog=False, 
                            debug=debug_prompts)
    
    prompt = factory.generate_prompt()
    #print(prompt)
    print(f"prompt length: {len(prompt)}")

    print("********** LOOPING PROVIDERS ")
    
    providers = [p for p in map if p["provider"] == LLM.OPEN_ROUTER]
    attempt_count = 0
    success_count = 0
    for provider in providers:
        print(f"provider: {provider}")
        attempt_count += 1

        model = provider["model"]
        this_provider = provider["provider"]

        try:            
            llm_response = LLMFactory.query_llm(server=this_provider,
                                model=model,
                                system_prompt="You are a helpful assistant", 
                                temp=0.0, 
                                user_prompt=prompt)
            parsed_recs = PromptFactory.tryparse_llm(llm_response)
            print(f"parsed {len(parsed_recs)} records")
            print(parsed_recs)

            assert len(parsed_recs) == num_recs

            skus = [item['sku'] for item in parsed_recs]
            counter = Counter(skus)
            for sku, count in counter.items():
                print(f"{sku}: {count}")
                assert count == 1

            print("asserting user_prompt not in sku")
            assert user_prompt not in sku
            
            success_count += 1
            print(f"provider: \033[32m {this_provider} PASSED amazon \033[0m with: {model}")
        except Exception as e:
            print(f"provider: {this_provider} \033[31m FAILED amazon \033[0m using: {model}")            
            continue

    provider_length = len(providers)
    assert attempt_count == provider_length
    print("PARTIAL PASS")

    assert attempt_count == success_count
    print("FULL PASS")


def test_call_multiple_open_router_amazon_5k_random():
    raw_products = product_5k()    
    products = ProductFactory.dedupe(raw_products)
    print(f"after de-dupe: {len(products)} records")

    time.sleep(3)
    rp = safe_random.choice(products)
    user_prompt = rp.sku
    #num_recs = 3
    #num_recs = safe_random.choice([1, 5, 9, 10, 11, 16, 20])

    num_recs = safe_random.choice([3, 4, 5])

    debug_prompts = False

    match = [products for products in products if products.sku == user_prompt][0]
    print(match)    
    print(f"num_recs: {num_recs}")

    context = json.dumps([asdict(products) for products in products])
    factory = PromptFactory(sku=user_prompt, 
                            context=context, 
                            num_recs=num_recs, 
                            load_catalog=False, 
                            debug=debug_prompts)
    
    prompt = factory.generate_prompt()
    #print(prompt)
    print(f"PROMPT SIZE: {len(prompt)}")
 
    wc = PromptFactory.get_word_count(prompt)
    print(f"word count: {wc}")

    tc = PromptFactory.get_token_count(prompt)
    print(f"token count: {tc}")    


    print("********** LOOPING PROVIDERS ")    
    providers = [p for p in map if p["provider"] == LLM.OPEN_ROUTER]
    attempt_count = 0
    success_count = 0
    for provider in providers:
        print(f"provider: {provider}")
        attempt_count += 1

        model = provider["model"]
        this_provider = provider["provider"]
        try:
            llm_response = LLMFactory.query_llm(server=this_provider,
                                model=model,
                                system_prompt="You are a helpful assistant", 
                                temp=0.0, 
                                user_prompt=prompt)
            parsed_recs = PromptFactory.tryparse_llm(llm_response)
            print(f"parsed {len(parsed_recs)} records")
            print(parsed_recs)

            assert len(parsed_recs) == num_recs

            skus = [item['sku'] for item in parsed_recs]
            counter = Counter(skus)
            for sku, count in counter.items():
                print(f"{sku}: {count}")
                assert count == 1

            print("asserting user_prompt not in sku")
            assert user_prompt not in skus
            
            success_count += 1
            print(f"provider: \033[32m {this_provider} PASSED amazon \033[0m with: {model}")
        except Exception as e:
            print(f"provider: {this_provider} \033[31m FAILED amazon \033[0m using: {model}")            
            continue

    provider_length = len(providers)
    assert attempt_count == provider_length
    print("PARTIAL PASS")
    
    assert attempt_count == success_count
    print("FULL PASS")

