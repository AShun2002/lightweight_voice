import os
from typing import Optional
from tavily import TavilyClient
from .logger import LoggerManager

logger=LoggerManager.get_logger()


TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    logger.warning("TAVILY_API_KEY环境变量未设置，Tavily功能将不可用")


_client:Optional[TavilyClient]=None

def get_tavily_client()-> TavilyClient:
    global _client
    if _client is None:
        if not TAVILY_API_KEY:
            raise   ValueError("TAVILY_API_KEY环境变量未设置，请先设置该变量以使用Tavily搜索。")
        _client = TavilyClient(api_key=TAVILY_API_KEY)
        logger.info("Tavily客户端初始化成功")
    return _client


def tavily_search(query: str,max_results: int=5) -> str:
    try:
        client = get_tavily_client()
        logger.info(f"执行Tavily搜索：{query}")
        response=client.search(query,max_results=max_results)
        results=response.get("results",[])
        if not results:
            return "未找到相关结果。"
        
        formatted=[]
        for i,res in enumerate(results,1):
            title=res.get("title","无标题")
            url=res.get("url","")
            content=res.get("content","").strip()
            if len(content)>300:
                content=content[:300]+"..."
            formatted.append(f"{i}. {title}\n  链接:{url}\n  摘要:{content}\n")

        result_textt="\n\n".join(formatted)
        logger.info(f"Tavily搜索完成，共找到{len(results)}个结果。")
        return result_textt
    
    except Exception as e:
        error_msg=f"执行Tavily搜索时出错：{str(e)}"
        logger.error(error_msg)
        return error_msg
    

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1:
        query=sys.argv[1]
    else:
        query="华为手机最新型号"
        print(f"测试Tavily搜索：")
        print(tavily_search(query,max_results=2))
