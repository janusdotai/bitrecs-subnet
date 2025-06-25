from openai import OpenAI

class OpenRouter:    
    def __init__(self, 
                 key,
                 model="google/gemini-flash-1.5-8b", 
                 system_prompt="You are a helpful assistant.", 
                 temp=0.0
        ):

        self.OPENROUTER_API_KEY = key
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.model = model
        self.system_prompt = system_prompt
        self.temp = temp


    def call_open_router(self, prompt) -> str:
        if not prompt or len(prompt) < 10:
            raise ValueError()

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.OPENROUTER_API_KEY,
        )

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://bitrecs.ai",
                "X-Title": "bitrecs"
            },
            model=self.model,
            messages=[
            {
                "role": "user",
                "content": prompt,
            }],
            temperature=self.temp,
            max_tokens=2048
        )
        thing = completion.choices[0].message.content                
        return thing