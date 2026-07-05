from typing import Optional, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
import operator

from .memory_sqlite import get_sqlite_saver
from .config import Config
from .llms import get_llm
from .tools import get_tools
from .models import Context, ResponseFormat
from .logger import LoggerManager

logger = LoggerManager.get_logger()

# ========== 1. 定义 Agent 状态 ==========
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    structured_response: Optional[ResponseFormat]

# ========== 系统提示词 ==========
SYSTEM_PROMPT = """你是一名专业的法律咨询顾问，同时也可以处理数据库查询。
你可以使用三个工具：
rag_law:用于获取中国现行法律的相关内容
tavily_search:用于通过网络检索获取一些最新资讯
sql_agent:用于使用自然语言查询数据库，执行复杂的SQL操作。
如果从问题中可以判断出用户是想要一些法律相关内容，比如"中国法律所规定的节假日休息情况是什么？"这样带"法律"字段的，或与法律条文相关的，使用rag_law工具；
如果用户的问题与最新资讯相关，比如"最近有哪些关于劳动法的新规定？"这样带"最近"字段的，使用tavily_search工具；
如果用户的问题与数据库查询相关，比如"查询所有员工的信息"这样带"查询"字段的，使用sql_agent工具。
你的回复必须是结构化的，包含以下字段:
- answer:主要回复内容
- tool_used:使用的工具名称(如果没有使用工具，则为空)
- legal_reference:引用的法律条文（如果有）
- search_result:网络搜索结果摘要（如果有）
- sql_result:SQL查询结果（如果有）
- confidence:你的回复的置信度（0-1之间）
请根据实际情况填写这些字段。"""


# ==========  LLM 推理节点 ==========
def llm_node(state: AgentState) -> dict:
    # 获取 LLM 和工具
    llm_chat, _ = get_llm(Config.LLM_TYPE)
    tools = get_tools()
    
    # 把工具绑定给 LLM（这样 LLM 才知道有哪些工具可以调用）
    llm_with_tools = llm_chat.bind_tools(tools)
    
    # 构造消息列表：系统提示 + 历史对话
    from langchain_core.messages import SystemMessage
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    # 调用 LLM
    logger.info("LLM 节点：正在推理...")
    response = llm_with_tools.invoke(messages)
    logger.info(f"LLM 节点：回复类型={'工具调用' if response.tool_calls else '直接回答'}")
    
    # 返回状态更新：追加一条 AI 消息
    # 因为 messages 字段用了 operator.add，所以返回列表就会自动追加
    return {"messages": [response]}


# ========== 工具调用节点 ==========
def tool_node(state: AgentState) -> dict:
    # 获取最后一条消息（就是 LLM 刚返回的）
    last_message = state["messages"][-1]
    
    # 获取工具列表
    tools = get_tools()
    # 把工具列表转成字典，方便按名字查找
    tool_map = {tool.name: tool for tool in tools}
    
    tool_messages = []
    
    # 遍历所有工具调用（LLM 可能一次调用多个工具）
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        
        logger.info(f"工具节点：调用工具 {tool_name}，参数：{tool_args}")
        
        # 找到对应的工具并执行
        if tool_name in tool_map:
            tool = tool_map[tool_name]
            try:
                result = tool.invoke(tool_args)
            except Exception as e:
                result = f"工具执行出错：{str(e)}"
                logger.error(f"工具 {tool_name} 执行出错：{e}")
        else:
            result = f"错误：找不到工具 {tool_name}"
            logger.error(f"找不到工具：{tool_name}")
        
        # 把工具结果包装成 ToolMessage
        # 注意：tool_call_id 必须和调用时的 id 对应上，LLM 才能知道是哪个调用的结果
        tool_message = ToolMessage(
            content=str(result),
            tool_call_id=tool_call_id,
            name=tool_name
        )
        tool_messages.append(tool_message)
    
    logger.info(f"工具节点：执行了 {len(tool_messages)} 个工具调用")
    
    # 返回状态更新：追加工具结果消息
    return {"messages": tool_messages}

# ========== 条件判断函数 ==========
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    
    # 检查最后一条消息有没有工具调用
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info("条件判断：需要调用工具")
        return "tools"
    
    logger.info("条件判断：不需要调用工具，结束")
    return "end"

# ========== 构建状态图 ==========
def build_graph(checkpointer=None):
    # 创建状态图
    workflow = StateGraph(AgentState)
    
    # 添加两个节点
    workflow.add_node("llm", llm_node)
    workflow.add_node("tools", tool_node)
    
    # 设置入口：从 llm 节点开始
    workflow.set_entry_point("llm")
    
    # 添加条件边：从 llm 节点出发，根据 should_continue 的返回值决定去哪里
    workflow.add_conditional_edges(
        "llm",                    # 起点：llm 节点
        should_continue,          # 判断函数
        {
            "tools": "tools",     # 返回 "tools" → 去 tools 节点
            "end": END            # 返回 "end" → 结束
        }
    )
    
    # 添加普通边：工具执行完，回到 llm 节点（让 LLM 看结果再回答）
    workflow.add_edge("tools", "llm")
    
    # 编译图，加上 checkpointer（记忆功能）
    app = workflow.compile(checkpointer=checkpointer)
    
    logger.info("Agent 状态图构建完成！")
    return app

import json

# ========== Agent 单例与封装 ==========
_agent_app = None

def _init_agent():
    global _agent_app
    if _agent_app is not None:
        return
    
    logger.info("正在初始化 CRM Agent...")
    
    # 获取 SQLite 记忆保存器
    checkpointer = get_sqlite_saver()
    
    # 构建状态图
    _agent_app = build_graph(checkpointer=checkpointer)
    
    logger.info("CRM Agent 初始化完成！")

def ask_agent(
    query: str,
    thread_id: str = "1",
    user_id: str = "1"
) -> dict:
    """
    向 CRM Agent 提问（对外接口）
    
    Args:
        query: 用户的问题文本
        thread_id: 会话ID（同一个ID的对话历史会被记住）
        user_id: 用户ID
    
    Returns:
        结构化的回答字典
    """
    # 确保 Agent 已初始化
    _init_agent()
    
    # 配置：指定 thread_id，用于记忆
    config = {"configurable": {"thread_id": thread_id}}
    
    # 构造用户消息
    user_message = HumanMessage(content=query)
    
    # 调用 Agent
    logger.info(f"收到用户问题：{query[:50]}...")
    result = _agent_app.invoke(
        {
            "messages": [user_message],
            "user_id": user_id
        },
        config=config
    )
    
    # 提取最后一条 AI 消息
    last_ai_message = None
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            last_ai_message = msg
            break
    
    # 尝试解析结构化输出（LLM 应该返回 JSON 格式）
    structured_result = {
        "answer": "",
        "tool_used": None,
        "legal_reference": None,
        "search_result": None,
        "sql_result": None,
        "confidence": None,
        "raw_message": ""
    }
    
    if last_ai_message:
        structured_result["raw_message"] = last_ai_message.content
        structured_result["answer"] = last_ai_message.content
        
        # 尝试从消息内容里解析 JSON（如果 LLM 按要求返回了 JSON）
        try:
            # 去掉可能的 markdown 代码块标记
            content = last_ai_message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                for key in structured_result.keys():
                    if key in parsed:
                        structured_result[key] = parsed[key]
        except (json.JSONDecodeError, TypeError):
            # 解析失败就用原始内容
            logger.warning("结构化输出解析失败，使用原始内容")
    
    # 检测使用了什么工具
    tool_used = []
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            tool_used.append(msg.name)
    if tool_used:
        structured_result["tool_used"] = ", ".join(tool_used)
    
    logger.info(f"Agent 回答完成，使用工具：{structured_result['tool_used']}")
    return structured_result

# ========== 测试模式 ==========
if __name__ == "__main__":
    print("=" * 50)
    print("CRM Agent 测试模式（LangGraph 版本）")
    print("输入 '退出' 结束")
    print("=" * 50)
    
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ["退出", "exit", "quit"]:
            print("再见！")
            break
        if not user_input:
            continue
        
        result = ask_agent(user_input)
        print(f"\nAgent：{result['answer']}")
        if result['tool_used']:
            print(f"使用工具：{result['tool_used']}")
        if result['legal_reference']:
            print(f"法律条文：{result['legal_reference']}")
        if result['sql_result']:
            print(f"SQL结果：{result['sql_result']}")