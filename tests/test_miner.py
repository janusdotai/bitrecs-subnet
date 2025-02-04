import json
import random
import time
import pytest
from bitrecs.commerce.product import CatalogProvider, ProductFactory
from bitrecs.llms.factory import LLM
from neurons.miner import do_work


def product_woo():
    woo_catalog = "./tests/data/woocommerce/product_catalog.csv" #2038 records
    catalog = ProductFactory.tryload_catalog_to_json(CatalogProvider.WOOCOMMERCE, woo_catalog)
    products = ProductFactory.convert(catalog, CatalogProvider.WOOCOMMERCE)
    return products


@pytest.mark.asyncio
async def test_bootleg_miner():
    num_recs = 6

    products = product_woo()
    query = random.choice(products).sku
    print(query)
    # Convert Product instances to dictionaries
    product_dicts = [product.to_dict() for product in products]
    context = json.dumps(product_dicts)

    st = time.perf_counter()
    result = await do_work(query, context, num_recs, LLM.OPEN_ROUTER, "llama3.1")
    et = time.perf_counter()
    print(f"Time to complete: {et - st} seconds")
    print(result)

    assert num_recs == len(result)
    assert query not in [rec["sku"] for rec in result]

    for rec in result:
        assert rec["sku"] in [product.sku for product in products]