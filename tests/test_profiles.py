import json
from typing import List
from bitrecs.llms.prompt_factory import PromptFactory
from bitrecs.utils.misc import ttl_cache
from bitrecs.commerce.user_profile import UserProfile
from bitrecs.commerce.product import CatalogProvider, Product, ProductFactory


@ttl_cache(ttl=900)
def product_1k() -> List[Product]:
    asos_catalog = "./tests/data/asos/sample_1k.csv" 
    catalog = ProductFactory.tryload_catalog_to_json(CatalogProvider.WOOCOMMERCE, asos_catalog)
    products = ProductFactory.convert(catalog, CatalogProvider.WOOCOMMERCE)    
    return products


def test_parse_profile_str():
    profile_str = '{"id": "123", "created_at": "2025-05-01T12:00:00Z", "cart": [], "orders": [], "site_config": {"profile": "ecommerce_retail_store_manager"} }'
    profile = UserProfile.tryparse_profile(profile_str)
    assert isinstance(profile, UserProfile)
    assert profile.id == "123"
    assert profile.created_at == "2025-05-01T12:00:00Z"
    assert profile.cart == []
    assert profile.orders == []
    assert profile.site_config == {"profile": "ecommerce_retail_store_manager"}


def test_parse_profile_dict():
    profile_dict = {
        "id": "456",
        "created_at": "2025-05-01T12:00:00Z",
        "cart": [],
        "orders": [],
        "site_config": {"profile": "ecommerce_retail_store_manager"}
    }
    profile = UserProfile.tryparse_profile(profile_dict)    
    assert isinstance(profile, UserProfile)
    assert profile.id == "456"
    assert profile.created_at == "2025-05-01T12:00:00Z"
    assert profile.cart == []
    assert profile.orders == []
    assert profile.site_config == {"profile": "ecommerce_retail_store_manager"}


def test_parse_profile_with_cart():
    cart_count = 5
    cart = product_1k()[:cart_count]
    cart_dicts = [product.to_dict() for product in cart]

    profile_dict = {
        "id": "123", 
        "created_at": "2025-05-01T12:00:00Z", 
        "cart": cart_dicts, 
        "orders": [], 
        "site_config": {"profile": "default"}
    }

    profile_str = json.dumps(profile_dict)    
    profile = UserProfile.tryparse_profile(profile_str)
    
    assert isinstance(profile, UserProfile)
    assert profile.id == "123"
    assert profile.created_at == "2025-05-01T12:00:00Z"
    assert len(profile.cart) == cart_count
    assert profile.orders == []
    assert profile.site_config == {"profile": "default"}


def test_parse_profile_invalid():
    invalid_profile = "This is not a valid profile"
    profile = UserProfile.tryparse_profile(invalid_profile)    
    assert profile is None
    invalid_dict = {"invalid_key": "value"}
    profile = UserProfile.tryparse_profile(invalid_dict)    
    assert profile is None


def test_persona_parse_default():
    thing = PromptFactory.PERSONAS["ecommerce_retail_store_manager"]    
    assert thing["description"] is not None
    assert thing["tone"] is not None
    assert thing["response_style"] is not None
    assert thing["priorities"] is not None

    

