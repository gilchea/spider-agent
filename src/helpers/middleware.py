from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config, wrap_model_call, ModelRequest, ModelResponse
from langgraph.runtime import Runtime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Any, Callable
from src.config import Config
from typing import Callable
from src.handlers.logging_config import logger
from typing import TypedDict
from src.helpers.llm import LLMFactory
from src.helpers.SYSTEM_PROMPT import GUARDRAIL_PROMPT
from src.helpers.skills import SKILLS
from src.helpers.tools import load_skill, create_db_tools, CustomState
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from typing import Literal


llm_factory = LLMFactory()

# define guardrail output structure
class GuardrailOutput(BaseModel):
    decision: Literal["ALLOW", "BLOCK"] = Field(description="Decision to allow or block the query BLOCK or ALLOW")
    reason: str = Field(description="Reason for the decision")

class Middleware1(AgentMiddleware):
    """Middleware bảo mật SQL: Sử dụng LLM để đánh giá ý định người dùng trước khi Agent xử lý và callback llm
    Middleware callback llm: tạo cơ chế thay thế llm khi một llm bị lỗi 
    """

    def __init__(self):
        super().__init__()
        self.guardrail_model = llm_factory.get_groq_model().with_structured_output(GuardrailOutput)
        # self.guardrail_model = llm_factory.get_groq_model().bind_tools([GuardrailOutput]) 
        # self.parser = PydanticToolsParser(tools=[GuardrailOutput])

        self.safety_prompt_template = GUARDRAIL_PROMPT
        self.gpt_model = llm_factory.get_gpt_model()
        self.groq_model = llm_factory.get_groq_model()
        self.gemini_model = llm_factory.get_gemini_model()     

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime):
        """Kiểm tra tin nhắn của người dùng trước khi Agent bắt đầu suy nghĩ."""
        if not state["messages"]:
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, HumanMessage):
            return None

        # Gọi LLM với cấu trúc Pydantic
        try:
            prompt = self.safety_prompt_template.format(user_input=last_message.content)
            result = self.guardrail_model.invoke(prompt)
            
            if result.decision.upper() == "BLOCK":
                return {
                        "messages": [{
                            "role": "assistant",
                            "content": f"🚫 **Truy cập bị chặn**\n**Lý do:** {result.reason}"
                        }],
                        "jump_to": "end"
                    }

            return None

        except Exception as e:
            # Fallback nếu LLM lỗi hoặc không parse được JSON
            print(f"Guardrail Error: {e}")
            return None 
    
    # @wrap_model_call
    def wrap_model_call(self, request: ModelRequest, handler: Callable) -> ModelResponse:
        gpt = self.gpt_model
        groq = self.groq_model
        gemini = self.gemini_model

        list_of_models = [gpt, groq, gemini]

        # Thử model chính (Handler gốc)
        try:
            return handler(request.override(model=gpt))
        except Exception as e1:
            logger.warning(f"Primary model failed: {e1}. Switching to fallbacks...")

            for i, model in enumerate(list_of_models):
                try:
                    logger.info(f"Attempting fallback {i+1}...")
                    return handler(request.override(model=model))
                except Exception as e:
                    logger.error(f"Fallback {i+1} failed: {e}")
                    continue

class Middleware2(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""

    def __init__(self):
        super().__init__()
        self.state_schema = CustomState 
        self.tools = [load_skill]

        """Initialize and generate the skills prompt from SKILLS."""
        # Build skills prompt from the SKILLS list
        skills_list = []
        for skill in SKILLS:
            skills_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
        self.skills_prompt = "\n".join(skills_list)  
                    
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync: Inject skill descriptions into system prompt."""
        # Build the skills addendum
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)