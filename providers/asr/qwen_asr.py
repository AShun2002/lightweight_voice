import dashscope
from .base import ASRBase

class QwenASR(ASRBase):
    """通义千问语音识别实现"""
    
    def __init__(self, api_key, model="qwen3-asr-flash"):
        dashscope.api_key = api_key
        self.model = model
    
    def transcribe(self, audio_file):
        """实现基类定义的 transcribe 方法"""
        messages = [
            {
                "role": "user",
                "content": [{"audio": audio_file}]
            }
        ]
        
        response = dashscope.MultiModalConversation.call(
            model=self.model,
            messages=messages,
            result_format="message"
        )
        
        if response.status_code == 200:
            return response.output.choices[0].message.content[0]["text"]
        else:
            raise Exception(f"ASR 识别失败：{response}")