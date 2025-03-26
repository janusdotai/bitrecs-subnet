import json
import re
import os
import pandas as pd
import bittensor as bt
import tiktoken


class PromptFactory:
    """
    Creates a bitrecs prompt for a given SKU and context.

    Args:
        sku (str): The SKU to generate recommendations for.
        context (str): The context to generate recommendations from.
        num_recs (int): The number of recommendations to generate.
        load_catalog (bool): Whether to load the catalog from a file.
        debug (bool): Whether to trace write the prompts.
        season (str): The current season.
        persona (str): The persona for the LLM to assume
    
    """
    def __init__(self, 
                 sku, 
                 context, 
                 num_recs=5, 
                 load_catalog=False, 
                 debug=False, 
                 season="spring/summer", 
                 persona="Ecommerce Retail Store Manager"):
        self.sku = sku
        self.context = context
        self.num_recs = num_recs
        if self.num_recs < 1 or self.num_recs > 20:
            raise ValueError("num_recs must be between 1 and 20")        
        self.load_catalog = load_catalog
        self.debug = debug
        self.catalog = []
        self.season = "spring/summer" if not season else season
        self.persona = "Ecommerce Retail Store Manager" if not persona else persona

    
    def generate_prompt(self) -> str:
        """
            Generates a text prompt for the given SKU and context.
        """
    
        bt.logging.info("PROMPT generating prompt: {}".format(self.sku))

        season = self.season
        persona = self.persona      
      
        prompt = """
        # PERSONA:

        <persona>{}</persona>

        You are a {} with decades of experience providing product recommendations to customers.
        You are goal oriented and your goal is to increase average order value and conversion rate for the store.
        You have a deep understanding of the full product catalog in the store.
        You have extensive knowledge of the products in the store and know each product attribute and how they contribute to the stores revenue.
        When a customer buys X you recommended Y because they are often bought together or in succession.        
        You do not show multiple colors or sizes of the same product (often called variants) in a set of recommendations.
        You produce a fair distribution of skus in the final list of recommendations.
        You also think outside the box and provide creative recommendations during different seasons.
        The current season is: <season>{}</season>.\n
        
        # INSTRUCTIONS

        Given the <query> make a list of {} product recommendations from the <context> provided.
    
        Consider your <persona> before making your list of {} product recommendations. 
        Only return products that exist in the <context> provided.
        **Very important** you must only return products that exist in the context. 
        Do not hallucinate.

        Here is the user query:
        <query>
        {}
        </query>        
        """.format(persona, persona, season, self.num_recs, self.num_recs, self.sku)

        if self.context and len(self.context) > 10:
            prompt += """\nHere is the list of products you can select your recommendations from:
        <context>{}</context>\n
        **Important** Only return products from the <context> provided.
                
        """.format(self.context)

        # prompt += """\n
        # # FINAL INSTRUCTIONS
        
        # 1) Load <persona> and <context> into your memory.
        # 2) Observe the user <query>.
        # 3) Find {} unique recommended products in the <context> that compliment the <query> and copy them to the return array.
        # 4) The products recommended should be products a customer would buy **after** they have purchased the product from <query>.
        # 5) Think step by step and consider the entire customer journey.                
        # 6) Do not recommend the same product as the <query> in the recommendations.
        # 7) The order of the recommendations is important. The first recommendation should be the most profitable and relevant to the <query>.
        # 8) Important information is in the 'name' field. Use this information to make your recommendations.
        # 9) Double check the potential return array for empty fields, invalid values, syntax errors, invalid string quotes, invalid characters.
        # 10) Never explain yourself, no small talk, just return the final recommendations in the correct array format. 
        # 11) Your final response should be a single JSON array of the recommendations.
        # 12) Do not alter the context JSON, return all fields as they are.
        # 13) Each recommendation should have a 'sku', 'name' and 'price' field.
        # 14) Each recommendation should be unique (use 'sku' as the key field for uniqueness).
        # 15) assert each recommendation is unique ('sku' is the key) and <query> not in recommendations.
        # 16) assert len(recommendations) == {}. If not, start over until assert is true.
        # 17) Never say 'Based on the provided query' or 'I have determined'. 
        # 18) Never explain yourself and no smalltalk.
        # 19) Return JSON.
            
        # """.format(self.num_recs, self.num_recs)

        prompt += """\n
        # FINAL INSTRUCTIONS
        
        1) Load <persona> and <context> into your memory.
        2) Observe the user <query> - this is a 'sku'. Find the matching master product from the <context> and memorize its 'name' and 'price'.
        3) Find {} unique products in the <context> that you think would go well with master product <query> and copy them to the return array.
        4) Never recommend the same product as the one in the <query> in your final recommendations.
        5) The order of the recommendations is important. The first recommendation should be the most profitable and relevant to the <query>.
        6) Important information is in the 'name' field. Use this information to make your recommendations.
        7) Double check the potential return array for empty fields, invalid values, syntax errors, invalid string quotes, invalid characters.
        8) Never explain yourself, no small talk, just return the final recommendations in the correct array format. 
        9) Your final response should be a single JSON array of the recommendations.
        10) Do not alter the context JSON, return all fields as they are.
        11) Each recommendation should have a 'sku', 'name' and 'price' field.
        12) Each recommendation should be unique (use 'sku' as the key field for uniqueness).
        13) assert each recommendation is unique ('sku' is the key) and <query> not in recommendations.
        14) assert len(recommendations) == {}. If not, start over until assert is true.
        15) Never say 'Based on the provided query' or 'I have determined'. 
        16) Never explain yourself and no smalltalk.
        17) Return JSON.
            
        """.format(self.num_recs, self.num_recs)

        prompt_length = len(prompt)
        bt.logging.info(f"LLM QUERY Prompt length: {prompt_length}")
        token_count = self.get_token_count(prompt)
        bt.logging.info(f"LLM QUERY Prompt Token count: {token_count}")

        if self.debug:
            bt.logging.debug("Prompt: {}".format(prompt))

        return prompt
        
    

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
        

    @staticmethod
    def get_token_count(prompt: str, encoding_name: str = "o200k_base") -> int:        
        encoding = tiktoken.get_encoding(encoding_name)        
        tokens = encoding.encode(prompt)
        return len(tokens)
    
    
    @staticmethod
    def get_word_count(prompt: str) -> int:
        return len(prompt.split())
    

class ExampleRecs:
    
    def example_recs() -> str:
        e = """"
        
        #  Example Queries:
        
        - <query>MH01-S-Orange</query>
        - <query>MH01-XL-Black</query>
        - <query>Chaz Kangeroo Hoodie - XL, Black</query>
        - <query>Chaz Kangeroo Hoodie - S, Orange</query>
        - <query>MS04-XL-Red</query>
        - <query>MS04-XS-Black</query>
        - <query>MS07-XL-Black</query>
        - <query>MS12</query>
        - <query>MT02-L-White</query>
        - <query>WS09-S-Red</query>
        - <query>WS09-S-White</query>
        - <query>WSH04-32-Green</query>
        - <query>WSH04-32-Orange</query>
        - <query>Breathe-Easy Tank</query>
        - <query>Breathe-Easy Tank - L, Purple</query>    
        - <query>Sprite Foam Yoga Brick</query>
        - <query>24-WG084</query>
        - <query>24-UG03</query>
        \n
        """
        return e
    
    
    def rt1() -> str:
        return """ 
        [
            {
                "sku": "MH01-S-Orange",         
                "name": "Chaz Kangeroo Hoodie - S, Orange",                
                "price" 52.00
            },
            {
                "sku": "MH01-XL-Black",         
                "name": "Chaz Kangeroo Hoodie - XL, Black",                
                "price" 52.00        
            },
            {
                "sku": "MS04-XL-Red",         
                "name": "Gobi HeatTec&reg; Tee - XL, Red",                
                "price" 29.00        
            },
            {
                "sku": "MS04-XS-Black",         
                "name": "Gobi HeatTec&reg; Tee - XS, Black",                
                "price" 29.00        
            },
            {
                "sku": "MS12",         
                "name": "Atomic Endurance Running Tee (Crew-Neck)",                
                "price" 29.00        
            },
            {
                "sku": "MT02-L-White",         
                "name": "Tristan Endurance Tank - L, White",                
                "price" 29.00           
            },
            {
                "sku": "WS09-S-Red",         
                "name": "Tiffany Fitness Tee - S, Red",                
                "price" 28.00           
            },
            {
                "sku": "WSH04-32-Green",         
                "name": "Artemis Running Short - 32, Green",                
                "price" 45.00           
            },
            {
                "sku": "WT09",         
                "name": "Breathe-Easy TanK",                
                "price" 34.00           
            },
            {
                "sku": "WT09-L-Purple",         
                "name": "Breathe-Easy Tank - L, Purple",                
                "price" 34.00           
            },
            {
                "sku": "24-WG084",         
                "name": "Sprite Foam Yoga Brick",                
                "price" 5.00           
            },
            {
                "sku": "24-UG03",         
                "name": "Harmony Lumaflex&trade; Strength Band Kit",                
                "price" 22.00           
            }

        ]"""