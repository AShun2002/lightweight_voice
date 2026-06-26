import asyncio
from providers.llm.qwen_llm import QwenLLM
from providers.asr.qwen_asr import QwenASR
from providers.tts.edge_tts import EdgeTTS
from crm import crm_manager

class VoiceChat:
    """
    语音对话主类
    把 ASR + LLM + TTS 串起来，提供统一的语音对话接口
    集成 CRM 用户信息管理
    """
    
    def __init__(self, config):
        """
        初始化
        :param config: 配置字典，包含各个模块的配置
        """
        # 初始化 LLM
        self.llm = QwenLLM(
            api_key=config["llm"]["api_key"],
            base_url=config["llm"]["base_url"],
            model=config["llm"].get("model", "qwen-turbo")
        )
        
        # 初始化 ASR
        self.asr = QwenASR(
            api_key=config["asr"]["api_key"],
            model=config["asr"].get("model", "qwen3-asr-flash")
        )
        
        # 初始化 TTS
        self.tts = EdgeTTS(
            voice=config["tts"].get("voice", "zh-CN-XiaoxiaoNeural")
        )
        
        # 系统提示词
        self.system_prompt = config.get("system_prompt", 
            "你是一个友好的语音助手，回答要简洁明了，适合语音播报，不要太长。")
        
        # 对话历史
        self.history = []
        
        # 会话 ID（后面会设置）
        self.session_id = None
    
    def set_session_id(self, session_id):
        """设置会话 ID，用于 CRM"""
        self.session_id = session_id
        # 确保用户档案存在
        crm_manager.create_profile(session_id)
    
    async def chat(self, audio_input_file, audio_output_file="reply.mp3"):
        """
        完整的语音对话
        :param audio_input_file: 输入的音频文件路径
        :param audio_output_file: 输出的音频文件路径
        :return: (用户说的话, AI回复的话, 输出音频路径)
        """
        # 1. ASR：语音转文字
        user_text = self.asr.transcribe(audio_input_file)
        
        # 2. LLM：AI 对话
        reply_text = self._chat_with_llm(user_text)
        
        # 3. TTS：文字转语音
        output_file = await self.tts.synthesize(reply_text, audio_output_file)
        
        # 4. CRM：提取用户信息
        if self.session_id:
            crm_manager.extract_user_info(self.session_id, self.history)
        
        return user_text, reply_text, output_file
    
    def chat_text(self, user_text):
        """
        文字对话（方便调试）
        :param user_text: 用户说的话
        :return: AI 回复的话
        """
        reply_text = self._chat_with_llm(user_text)
        
        # CRM：提取用户信息
        if self.session_id:
            crm_manager.extract_user_info(self.session_id, self.history)
        
        return reply_text
    
    def _chat_with_llm(self, user_text):
        """内部方法：调用 LLM 对话"""
        messages = [{"role": "system", "content": self.system_prompt}] + self.history
        messages.append({"role": "user", "content": user_text})
        
        reply_text = self.llm.chat(messages)
        
        # 更新历史
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply_text})
        
        return reply_text
    
    def get_user_profile(self):
        """获取当前用户的 CRM 档案"""
        if self.session_id:
            return crm_manager.get_profile(self.session_id)
        return None
    
    def clear_history(self):
        """清空对话历史（不清空 CRM 信息）"""
        self.history = []