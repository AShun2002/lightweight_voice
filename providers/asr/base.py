from abc import ABC, abstractmethod

class ASRBase(ABC):
    """ASR 基类，定义所有语音识别必须实现的接口"""
    
    @abstractmethod
    def transcribe(self, audio_file):
        """
        语音转文字
        :param audio_file: 音频文件路径
        :return: 识别出的文字
        """
        pass