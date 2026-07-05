from langchain_core.tools import tool
from .models import Context
from .logger import LoggerManager
from .rag_law import rag_law_query
from .tavily_search import tavily_search as tavily_search_func


logger=LoggerManager.get_logger()


from .sql_agent import query_sql_agent


def get_tools():
    @tool ("rag_law",description="利用法律条文知识库检索法条。")
    def rag_law(query:str)->str:
        return rag_law_query(query)
    
    @tool("tavily_search",description="根据用户想要获取最新资讯的问题进行网络检索。")
    def tavily_search(query:str)->str:
        return tavily_search_func(query)
    
    @tool("sql_agent",description="使用自然语言查询数据库，执行复杂的SQL操作")
    def sql_agent(query:str)->str:
        return query_sql_agent(query)

    tools=[
        rag_law,
        tavily_search,
        sql_agent
    ]

    logger.info(f"获取并提供的工具列表：{tools}")

    return tools