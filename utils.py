import requests
from openai import OpenAI
import instructor


class LLMAdapter:
    # for compatibility with openai behavior with Text-Generation-Inference
    def __init__(self, url_or_name, use_openai, configs) -> None:
        self.use_openai = use_openai
        self.model_name = url_or_name
        if self.use_openai:
            self.client = instructor.patch(OpenAI())
        self.configs = configs

    def generate(self, sys_prompt, user_prompt):
        if self.use_openai:
            return self.generate_openai(sys_prompt, user_prompt)
        else:
            return self.generate_tgilm(sys_prompt, user_prompt)
        
    def generate_openai(self, sys_prompt, user_prompt, **kwargs):
        return self.client.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": sys_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            **kwargs
        )

    def generate_tgilm(self, model_name, sys_prompt, user_prompt):
        prompt = f"### System:\n{sys_prompt}\n### User:\n{user_prompt}\n### Agent:"

        return requests.post(
            f"{model_name}/generate",
            json={
                "inputs": prompt,
                "parameters": self.configs
            }
        ).json()['generated_text']
    
