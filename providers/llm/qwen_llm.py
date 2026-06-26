from openai import OpenAI
from .base import LLMBase

class QwenLLM(LLMBase):
    """通义千问 LLM 实现"""
    
    def __init__(self, api_key, base_url, model="qwen-turbo"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def chat(self, messages):
        """实现基类定义的 chat 方法"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content