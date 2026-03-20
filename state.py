from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    instance_id: str
    db_name: str
    question: str
    external_knowledge: Optional[str]
    # Các thành phần nội tại của agent
    selected_tables: List[str]
    sql_query: str
    execution_result: Optional[str]
    error: Optional[str]
    is_valid: bool