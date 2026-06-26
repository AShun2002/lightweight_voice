from abc import ABC, abstractmethod

class TTSBase(ABC):
    """TTS 基类，定义所有语音合成必须实现的接口"""
    
    @abstractmethod
    async def synthesize(self, text, output_file):
        """
        文字转语音
        :param text: 要合成的文字
        :param output_file: 输出音频文件路径
        :return: 输出音频文件路径
        """
        pass