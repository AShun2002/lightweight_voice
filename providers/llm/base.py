from abc import ABC, abstractmethod

class LLMBase(ABC):
    """LLM 基类，定义所有 LLM 必须实现的接口"""
    
    @abstractmethod
    def chat(self, messages):
        """
        对话接口
        :param messages: 对话历史，格式 [{"role": "user", "content": "..."}]
        :return: AI 回复的文字
        """
        pass
    
    def chat_single(self, user_text, system_prompt=None):
        """
        单轮对话（便捷方法）
        :param user_text: 用户说的话
        :param system_prompt: 系统提示词
        :return: AI 回复的文字
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})
        return self.chat(messages)