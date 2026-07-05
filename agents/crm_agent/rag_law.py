import os
from pathlib import Path
from typing import List, Optional
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from .llms import get_llm
from .logger import LoggerManager
from langchain_openai import OpenAIEmbeddings
from .llms import MODEL_CONFIGS,DEFAULT_LLM_TYPE
logger=LoggerManager.get_logger()
LAW_DOC_PATH = Path(__file__).parent / "data" / "中华人民劳动法.txt"
CHROMA_PERSIST_DIR = Path(__file__).parent / "chroma_law"
COLLECTION_NAME="labor_law"
_vector_store:Optional[Chroma] = None
def get_embeddings():
    config=MODEL_CONFIGS.get(DEFAULT_LLM_TYPE,MODEL_CONFIGS["dashscope"])
    api_key=config["api_key"]
    model_name=config["embedding_model"]
    base_url=config["base_url"]
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url
    )
def load_and_split_documents()-> List[Document]:
    if not LAW_DOC_PATH.exists():
        raise FileNotFoundError(f"法律条文文件不存在: {LAW_DOC_PATH}")
    loader=TextLoader(str(LAW_DOC_PATH),encoding="utf-8")
    documents=loader.load()
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50,separators=["\n","。","，"," "])
    splits=text_splitter.split_documents(documents)
    logger.info(f"法律条文加载完成，共有 {len(documents)}原始文档，分割为{len(splits)}个块")
    return splits
def get_vector_store()-> Chroma:
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    
    logger.info(f"正在初始化法律条文向量储存(Chroma)...")
    splits=load_and_split_documents()
    embeddings=get_embeddings()
    vector_store=Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
        collection_name=COLLECTION_NAME
    )
    _vector_store=vector_store
    logger.info(f"法律条文向量储存初始化完成,持久化目录: {CHROMA_PERSIST_DIR}")
    return _vector_store
    
def retrieve_law(query:str,k:int=3)->List[Document]:
    vector_store=get_vector_store()
    docs=vector_store.similarity_search(query,k=k)
    return docs
def format_docs(docs:List[Document])->str:
    formatted=[]
    for i,doc in enumerate(docs,1):
        content=doc.page_content.strip()
        formatted.append(f"{i}. {content}")
    return "\n\n".join(formatted)
def rag_law_query(query:str)->str:
    try:
        docs=retrieve_law(query,k=3)
        if not docs:
            return "没有找到相关法律条文"
        return format_docs(docs)
    except Exception as e:
        logger.error(f"查询法律条文失败: {e}")
        return f"法律条文检索时发生错误：{str(e)}"
    
    
    
if __name__=="__main__":
    test_query="请帮我解释一下劳动法中关于劳动者的权益保障"
    print(f"测试查询：{test_query}")
    result=rag_law_query(test_query)
    print(f"查询结果：\n{result}")
