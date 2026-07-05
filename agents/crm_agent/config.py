import os
from pathlib import Path

# 获取当前文件所在目录（crm_agent/）
BASE_DIR = Path(__file__).parent

class Config:
    LOG_FILE = str(BASE_DIR / "logfile" / "app.log")
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    MAX_BYTES = 5 * 1024 * 1024
    BACKUP_COUNT = 3
    LLM_TYPE = "dashscope"
    MEMORY_DB_PATH = str(BASE_DIR / "data" / "memory.db")
    SQL_AGENT_DB_PATH = str(BASE_DIR / "data" / "app.db")
