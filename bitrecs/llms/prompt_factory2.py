

import re
import json
import time
import tiktoken
import bittensor as bt
from typing import List
from datetime import datetime
from bitrecs.commerce.product import Product, ProductFactory


class PromptFactory2:
    
    PERSONAS = {
        "luxury_concierge": {
            "description": "an elite American Express-style luxury concierge with impeccable taste and a deep understanding of high-end products across all categories. You cater to discerning clients seeking exclusivity, quality, and prestige",
            "tone": "sophisticated, polished, confident",
            "response_style": "Recommend only the finest, most luxurious products with detailed descriptions of their premium features, craftsmanship, and exclusivity. Emphasize brand prestige and lifestyle enhancement",
            "priorities": ["quality", "exclusivity", "brand prestige"]
        },
        "general_recommender": {
            "description": "a friendly and practical product expert who helps customers find the best items for their needs, balancing seasonality, value, and personal preferences across a wide range of categories",
            "tone": "warm, approachable, knowledgeable",
            "response_style": "Suggest well-rounded products that offer great value, considering seasonal relevance and customer needs. Provide pros and cons or alternatives to help the customer decide",
            "priorities": ["value", "seasonality", "customer satisfaction"]
        },
        "discount_recommender": {
            "description": "a savvy deal-hunter focused on moving inventory fast. You prioritize low prices, last-minute deals, and clearing out overstocked or soon-to-expire items across all marketplace categories",
            "tone": "urgent, enthusiastic, bargain-focused",
            "response_style": "Highlight steep discounts, limited-time offers, and low inventory levels to create a sense of urgency. Focus on price savings and practicality over luxury or long-term value",
            "priorities": ["price", "inventory levels", "deal urgency"]
        },
        "ecommerce_retail_store_manager": {
            "description": "an experienced e-commerce retail store manager with a strategic focus on optimizing sales, customer satisfaction, and inventory turnover across a diverse marketplace",
            "tone": "professional, practical, results-driven",
            "response_style": "Provide balanced recommendations that align with business goals, customer preferences, and current market trends. Include actionable insights for product selection",
            "priorities": ["sales optimization", "customer satisfaction", "inventory management"]
        }
    }

    def __init__(self, 
                 sku, 
                 context, 
                 num_recs=5, 
                 load_catalog=False, 
                 debug=False, 
                 season="spring/summer", 
                 persona="ecommerce_retail_store_manager"):
        self.sku = sku
        self.context = context
        self.num_recs = num_recs
        if self.num_recs < 1 or self.num_recs > 20:
            raise ValueError("num_recs must be between 1 and 20")        
        self.load_catalog = load_catalog
        self.debug = debug
        self.catalog = []
        self.season = "spring/summer" if not season else season
        self.persona = "ecommerce_retail_store_manager" if not persona else persona
        
        if self.persona not in self.PERSONAS:
            raise ValueError(f"Invalid persona. Available personas: {', '.join(self.PERSONAS.keys())}")
 

    def list_available_personas(self):
        """Return a list of available personas."""
        return list(self.PERSONAS.keys())
        

    def generate_prompt_with_cart(self, cart: List[Product]) -> str:
        if len(cart) == 0:
            raise ValueError("Cart cannot be empty")
        self.cart = cart
        self.update_context()
        return self.generate_prompt()
    

    def update_context(self) -> str:
        raise NotImplementedError("update_context")
        st = time.perf_counter()
        if not self.context:
            return ""
        products = ProductFactory.try_parse_products(self.context)
        if len(products) == 0:
            return ""
        for item in self.cart:
            products = [p for p in products if p.sku != item.sku]
        #products = [p for p in products if p.sku != self.sku] #TODO: llm assist 
        et = time.perf_counter()
        diff = et - st
        bt.logging.info(f"Updated context in {diff} seconds")   
        print(f"Updated context in {diff} seconds")     
        products = sorted(products, key=lambda x: (x.name.lower(), x.price))
        self.context = json.dumps([p.to_dict() for p in products])
        return self.context


    def generate_prompt(self) -> str:
        """Generates a text prompt for product recommendations with persona details."""
        bt.logging.info("PROMPT generating prompt: {}".format(self.sku))

        today = datetime.now().strftime("%Y-%m-%d")
        season = self.season
        persona_data = self.PERSONAS[self.persona]

        prompt = f"""# PERSONA
    <persona>{self.persona}</persona>

    You embody: {persona_data['description']}
    Your mindset: {persona_data['tone']}
    Your expertise: {persona_data['response_style']}
    Core values: {', '.join(persona_data['priorities'])}

    Your role:
    - Increase average order value and conversion rate
    - Use deep product catalog knowledge
    - Understand product attributes and revenue impact
    - Recommend complementary products (X → Y)
    - Avoid variant duplicates (same product in different colors/sizes)
    - Consider seasonal relevance

    Current season: <season>{season}</season>
    Today's date: {today}

    # TASK
    Given a product SKU, select {self.num_recs} complementary products from the provided context.
    Use your persona qualities to THINK about which products to select, but return ONLY a JSON array.
    Evaluate each products name and price fields when making your recommendations.

    # INPUT
    Query SKU: <query>{self.sku}</query>

    Available products:
    <context>
    {self.context}
    </context>

    # OUTPUT REQUIREMENTS
    - Return ONLY a JSON array.
    - Each object must have: sku, name, price.
    - Important information is in the 'name' field. Use this information to help make your recommendations.
    - Must return exactly {self.num_recs} items.
    - Items must exist in context.
    - No duplicates.
    - Query SKU must not be included.
    - Order by relevance/profitability.
    - No explanations or text outside the JSON array.

    Example format:
    [
        {{"sku": "ABC", "name": "Product Name", "price": "100"}},
        {{"sku": "DEF", "name": "Another Product", "price": "200"}}
    ]"""

        prompt_length = len(prompt)
        bt.logging.info(f"LLM QUERY Prompt length: {prompt_length}")
        token_count = PromptFactory2.get_token_count(prompt)
        bt.logging.info(f"LLM QUERY Prompt Token count: {token_count}")

        if self.debug:            
            bt.logging.debug(f"Persona: {self.persona}")
            bt.logging.debug(f"Season {season}")
            bt.logging.debug(f"Values: {', '.join(persona_data['priorities'])}")
            bt.logging.debug(f"Prompt: {prompt}")
            print(prompt)

        return prompt
    
    
    @staticmethod
    def get_token_count(prompt: str, encoding_name: str = "o200k_base") -> int:        
        encoding = tiktoken.get_encoding(encoding_name)        
        tokens = encoding.encode(prompt)
        return len(tokens)
    
    
    @staticmethod
    def get_word_count(prompt: str) -> int:
        return len(prompt.split())
    

    @staticmethod
    def tryparse_llm(input_str: str) -> list:
        """
        Take raw LLM output and parse to an array 

        """
        try:
            if not input_str:
                bt.logging.error("Empty input string tryparse_llm")   
                return []
            input_str = input_str.replace("```json", "").replace("```", "").strip()
            pattern = r'\[.*?\]'
            regex = re.compile(pattern, re.DOTALL)
            match = regex.findall(input_str)        
            for array in match:
                try:
                    llm_result = array.strip()
                    return json.loads(llm_result)
                except json.JSONDecodeError:                    
                    bt.logging.error(f"Invalid JSON in prompt factory: {array}")
            return []
        except Exception as e:
            bt.logging.error(str(e))
            return []
