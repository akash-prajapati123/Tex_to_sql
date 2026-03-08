from typing import TypedDict, Optional

class AgentState(TypedDict):
    question: str
    sql_query: Optional[str]
    sql_error: Optional[str]
    db_results: Optional[str]
    final_answer: Optional[str]
    retries: int
