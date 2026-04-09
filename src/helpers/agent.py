###helpers/agent.py
"""
Agent module for NL2SQL system.

This module is responsible for:
- Initializing LLM models
- Configuring SSL for secure API communication
- Creating NL2SQL agents with tool integrations
- Providing utility functions for dataset filtering

The agent leverages LangChain's tool-calling capabilities to
convert natural language queries into SQL queries and execute them.
"""
# from src.helpers.middleware import GuardrailsDecisionMiddleware
import os
import httpx
from typing import Any, Callable, Dict, List, Optional, Union

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config, wrap_model_call, ModelRequest, ModelResponse
from src.helpers.tools import load_skill
# from langchain_core.agents import AgentAction, AgentFinish
# from langchain_core.messages import BaseMessage
# # Nếu bạn cần phản hồi từ Tool
# from langchain_core.tools import ToolException

# from typing import Any

from langchain.agents.middleware import hook_config
# from langgraph.runtime import Runtime
# from typing import Any

from src.config import Config
from src.helpers.tools import create_db_tools
from src.helpers.middleware import Middleware1, Middleware2
# from src.handlers.database import DatabaseManager
from src.handlers.logging_config import logger
from src.helpers.SYSTEM_PROMPT import SYSTEM_PROMPT

# -------------------------------------------------------------------
# SSL CONFIGURATION
# -------------------------------------------------------------------

cert_path = str(Config.CERT)

try:
    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path

    # ssl._create_default_https_context = ssl.create_default_context(
    #     cafile=cert_path
    # )
    ####

    logger.info("SSL configured successfully with cert: %s", cert_path)

except Exception as e:
    logger.error("Failed to configure SSL: %s", str(e), exc_info=True)
    raise RuntimeError(f"SSL configuration failed: {str(e)}") from e

# -------------------------------------------------------------------
# AGENT FACTORY
# -------------------------------------------------------------------

def create_nl2sql_agent(db_id: str):
    """
    Create an NL2SQL agent for a specific database.

    This function initializes the database manager, loads tools,
    configures the language model, and builds a LangChain agent.

    Args:
        db_id (str): Identifier of the target SQLite database.

    Returns:
        Agent: A configured LangChain agent instance.

    Raises:
        RuntimeError: If agent creation fails.
    """
    try:
        logger.info("Creating NL2SQL agent for db_id: %s", db_id)

        # -------------------------------------------------------------------
        # MODEL CONFIGURATION
        # -------------------------------------------------------------------

        # Thiết lập HTTP client với SSL cho Groq (nếu cần thiết)
        groq_http_client = httpx.Client(
                            verify=False
                        )
        
        model_groq = ChatGroq(
            model=Config.GROQ_MODEL_NAME,
            groq_api_key=Config.GROQ_API_KEY,
            temperature=0,
            http_client=groq_http_client
            
        )

        # Thiết lập HTTP client với SSL cho Gemini
        gemini_http_client = httpx.Client(
            verify=str(Config.CERT)  # giữ SSL
        )

        model_gemini = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL_NAME,
            api_key=Config.GEMINI_API_KEY, # Lưu ý: dùng api_key thay vì google_api_key ở các bản mới
            client_args={
                "http_client": httpx.Client(verify=str(Config.CERT))
            }
        )

        # Thiết lập HTTP client cho GitHub (nếu bạn cần bỏ qua verify hoặc dùng cert riêng)
        github_http_client = httpx.Client(
            verify=False # Hoặc str(Config.CERT) tùy môi trường của bạn
        )

        model_gpt = ChatOpenAI(
            model=Config.GPT_MODEL_NAME,
            api_key=Config.GITHUB_KEY,
            base_url=Config.GITHUB_ENDPOINT,
            http_client=github_http_client,
            temperature=0
        )

        agent = create_agent(
            model = model_gpt,
            tools=create_db_tools(db_id),
            system_prompt=SYSTEM_PROMPT,
            checkpointer=InMemorySaver(),
            middleware = [
                # Middleware2(),
                Middleware1()
            ]
        )

        logger.info("NL2SQL agent created successfully for db_id: %s", db_id)

        return agent

    except Exception as e:
        logger.error(
            "Failed to create NL2SQL agent for db_id: %s",
            db_id,
            exc_info=True
        )
        raise RuntimeError(f"Agent creation failed: {str(e)}") from e
    