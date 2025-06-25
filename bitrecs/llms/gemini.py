from openai import OpenAI

class Gemini:
    def __init__(self, 
                 key, 
                 model="gemini-2.0-flash-lite-001", 
                 system_prompt="You are a helpful assistant.", 
                 temp=0.0):
        
        self.GEMINI_API_KEY = key
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        self.model = model
        self.system_prompt = system_prompt
        self.temp = temp
        

    def call_gemini(self, prompt) -> str:
        if not prompt or len(prompt) < 10:
            raise ValueError()

        client = OpenAI(api_key=self.GEMINI_API_KEY,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://bitrecs.ai",
                "X-Title": "bitrecs"
            }, 
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temp,
            max_tokens=2048
        )
        thing = completion.choices[0].message.content                
        return thing