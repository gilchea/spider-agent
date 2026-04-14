from typing import Annotated, List
from typing_extensions import TypedDict # Hoặc từ typing nếu dùng Python 3.12+
import operator

class CustomState(TypedDict): # Nên dùng TypedDict cho LangGraph State
    messages: Annotated[List, operator.add]
    # Sử dụng operator.add để khi update [skill_name], nó sẽ cộng dồn vào list cũ
    skills_loaded: Annotated[list[str], operator.add]