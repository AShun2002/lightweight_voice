import os
from dotenv import load_dotenv, find_dotenv  
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from .logger import LoggerManager

load_dotenv(find_dotenv())

logger=LoggerManager.get_logger()
MODEL_CONFIGS = {
    "dashscope": {
        "base_url":"https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "chat_model":"qwen-plus",
        "embedding_model":"text-embedding-v2"
    }
}
DEFAULT_LLM_TYPE="dashscope"
DEFAULT_TEMPERATURE=0
class LLMInitializationError(Exception):
    pass
def initialize_llm(llm_type:str=DEFAULT_LLM_TYPE)->tuple[ChatOpenAI,OpenAIEmbeddings]:
    try:
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(f"不支持的LLM类型:{llm_type}.可用的类型: {list(MODEL_CONFIGS.keys())}")
        
        config=MODEL_CONFIGS[llm_type]
        llm_chat=ChatOpenAI(
            model=config["chat_model"],
            temperature=DEFAULT_TEMPERATURE,
            base_url=config["base_url"],
            api_key=config["api_key"],
            timeout=30,
            max_retries=2
        )
        llm_embedding=OpenAIEmbeddings(
            model=config["embedding_model"],
            base_url=config["base_url"],
            api_key=config["api_key"]
        )
        logger.info(f"成功初始化LLM:{llm_type}")
        return llm_chat,llm_embedding
    
    except ValueError as ve:
        logger.error(f"LLM配置错误:{ve}")
        raise LLMInitializationError(f"LLM配置错误:{ve}")
    except Exception as e:
        logger.error(f"初始化LLM失败:{e}")
        raise LLMInitializationError(f"初始化LLM失败:{e}")
    
def get_llm(llm_type:str=DEFAULT_LLM_TYPE)->ChatOpenAI:
    try:
        return initialize_llm(llm_type)
    except LLMInitializationError as e:
        logger.warning(f"使用默认配置重试:{e}")
        if llm_type!=DEFAULT_LLM_TYPE:
            return get_llm(DEFAULT_LLM_TYPE)
        raise
if __name__=="__main__":
    try:
        llm_openai,llm_embedding=get_llm("dashscope")
        llm_invalid=get_llm("invalid_type")
    except LLMInitializationError as e:
        logger.error(f"程序终止:{e}")
