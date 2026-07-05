from dataclasses import dataclass
@dataclass
class Context:
    user_id: str
@dataclass
class ResponseFormat:
    answer: str
    tool_used: str|None=None
    legal_reference: str|None=None
    search_result: str|None=None
    sql_result: str|None=None
    confidence: float|None=None
