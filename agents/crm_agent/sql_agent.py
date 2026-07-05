import os
from typing import Optional
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from .llms import get_llm
from .config import Config
from .logger import LoggerManager

logger=LoggerManager.get_logger()


_sql_agent_instance=None

def get_sql_agent():
    global _sql_agent_instance
    if _sql_agent_instance is None:
        db_path=Config.SQL_AGENT_DB_PATH
        dir_path=os.path.dirname(db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"创建SQL数据库目录: {dir_path}")

        if not os.path.exists(db_path):
            create_example_db(db_path)
            logger.info(f"创建示例数据库: {db_path}")


        db_uri=f"sqlite:///{db_path}"
        logger.info(f"连接SQL数据库: {db_uri}")
        db=SQLDatabase.from_uri(db_uri)

        llm_chat,_=get_llm(Config.LLM_TYPE)

        toolkit=SQLDatabaseToolkit(db=db, llm=llm_chat)

        agent=create_sql_agent(
            llm=llm_chat,
            toolkit=toolkit,
            agent_type="zero-shot-react-description",
            verbose=True,
            handle_parsing_errors=True,
        )
        _sql_agent_instance=agent
        logger.info("SQL Agent初始化完成")
    return _sql_agent_instance

def create_example_db(db_path: str):
    import sqlite3
    conn=sqlite3.connect(db_path)
    cursor=conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            age INTEGER,
            city TEXT
        )
    ''')

    cursor.executemany(
        "INSERT INTO users (name, email, age, city) VALUES (?, ?, ?, ?)",
        [
            ("张三","zhangsan@example.com", 30, "北京"),
            ("李四","lisi@example.com", 25, "上海"),
            ("王五","wangwu@example.com", 35, "广州"),
            ("赵六","zhaoliu@example.com", 28, "深圳"),
        ]
    )


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL,
            stock INTEGER,
            category TEXT
        )
    ''')

    cursor.executemany(
        "INSERT INTO products (name,category,price, stock) VALUES (?, ?, ?,?)",
        [
            ("笔记本电脑", "电子产品", 5000, 10),
            ("智能手机", "电子产品", 3000, 20),
            ("办公椅", "家具", 200, 30),
            ("咖啡机","家电",1500,20),
        ]
    )

    conn.commit()
    conn.close()
    logger.info("示例数据库创建完成,包含users和products表")


def query_sql_agent(question: str) -> str:
    try:
        agent=get_sql_agent()
        logger.info(f"执行SQL Agent查询: {question}")
        result=agent.invoke({"input":question})
        output=result.get("output",str(result))
        logger.info(f"SQL Agent 查询完成")
        return output
    except Exception as e:
        error_msg=f"SQL Agent查询时发生错误: {str(e)}"
        logger.error(error_msg)
        return error_msg
    
if __name__ == '__main__':
    print("测试SQL Agent...")
    answer=query_sql_agent("表中有多少条记录？")
    print(f"回答:{answer}")