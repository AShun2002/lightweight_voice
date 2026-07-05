from langgraph.checkpoint.memory import MemorySaver
from .logger import LoggerManager

logger = LoggerManager.get_logger()

_memory_saver_instance = None

def get_sqlite_saver():
    """
    获取记忆保存器（MemorySaver 内存版）
    
    注意：函数名还叫 get_sqlite_saver，是为了兼容其他地方的调用
    实际用的是 MemorySaver，重启程序后记忆会丢失
    """
    global _memory_saver_instance
    if _memory_saver_instance is None:
        logger.info("初始化 MemorySaver（内存版）")
        _memory_saver_instance = MemorySaver()
    return _memory_saver_instance

def clear_memory():
    """清除记忆"""
    global _memory_saver_instance
    _memory_saver_instance = None
    logger.info("已清除记忆")
