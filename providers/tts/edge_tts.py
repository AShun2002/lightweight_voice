import edge_tts
from .base import TTSBase

class EdgeTTS(TTSBase):
    """Edge TTS 语音合成实现"""
    
    def __init__(self, voice="zh-CN-XiaoxiaoNeural"):
        self.voice = voice
    
    async def synthesize(self, text, output_file):
        """实现基类定义的 synthesize 方法"""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)
        return output_file