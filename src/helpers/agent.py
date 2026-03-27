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

import os
import json
import ssl
import httpx
from typing import Callable, List, Dict, Any

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek
from langchain.agents.middleware.model_fallback import ModelFallbackMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

from src.config import Config
from src.helpers.tools import create_db_tools
# from src.handlers.database import DatabaseManager
from src.helpers.logging_config import logger
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

        # Initialize DatabaseManager (kept for consistency, even if not directly used here)
        # db_manager = DatabaseManager(db_id)

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

        # model_qwen = ChatGoogleGenerativeAI(
        #     model=Config.QWEN_MODEL_NAME,
        #     google_api_key=Config.QWEN_API_KEY
        # )

        # Thiết lập HTTP client với SSL cho Gemini
        gemini_http_client = httpx.Client(
            verify=str(Config.CERT)  # giữ SSL
        )

        model_gemini = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL_NAME,
            google_api_key=Config.GEMINI_API_KEY,
            http_client=gemini_http_client
        )

        deepseek_http_client = httpx.Client(
            verify= False 
        )

        model_deepseek = ChatDeepSeek(
        model=Config.DEEPSEEK_MODEL_NAME,
        api_key=Config.DEEPSEEK_API_KEY,
        temperature=0,
        http_client=deepseek_http_client
        )

        @wrap_model_call
        def dynamic_model_selection(request: ModelRequest, handler: Callable) -> ModelResponse:
            try:
                return handler(request.override(model=model_groq))
            except Exception as e1:
                logger.warning("Groq failed: %s", str(e1))

                try:
                    return handler(request.override(model=model_gemini))
                except Exception as e2:
                    logger.error("Both models failed: %s | %s", str(e1), str(e2))
                    raise e2
        # -------------------------------------------------------------------
        # AGENT CREATION
        # -------------------------------------------------------------------

        # agent = create_agent(
        #     model=model_deepseek,
        #     tools=create_db_tools(db_id),
        #     system_prompt=SYSTEM_PROMPT,
        #     # middleware=[ModelFallbackMiddleware(model_groq, model_gemini)],
        #     checkpointer=InMemorySaver()
        # )

        # agent = create_agent(
        #     model=model_gemini,
        #     tools=create_db_tools(db_id),
        #     system_prompt=SYSTEM_PROMPT,
        #     checkpointer=InMemorySaver(max_history=20)
        # )

        # agent = create_agent(
        #     model=model_groq,
        #     tools=create_db_tools(db_id),
        #     system_prompt=SYSTEM_PROMPT,
        #     checkpointer=InMemorySaver()
        # )

        agent = create_agent(
            model=model_groq,
            tools=create_db_tools(db_id),
            system_prompt=SYSTEM_PROMPT,
            checkpointer=InMemorySaver(),
            middleware=[dynamic_model_selection]
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
    