"""
LLM module for NL2SQL system.

This module is responsible for:
Initializing LLM models

"""

import httpx
import os
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

from src.handlers.logging_config import logger
from src.config import Config

# -------------------------------------------------------------------
# SSL CONFIGURATION
# -------------------------------------------------------------------

cert_path = str(Config.CERT)

try:
    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path

    logger.info("SSL configured successfully with cert: %s", cert_path)

except Exception as e:
    logger.error("Failed to configure SSL: %s", str(e), exc_info=True)
    raise RuntimeError(f"SSL configuration failed: {str(e)}") from e

class LLMFactory:
    def __init__(self):
        # Thiết lập HTTP client với SSL cho Groq (nếu cần thiết)
        self.groq_http_client = httpx.Client(
            verify=False
        )

        # Thiết lập HTTP client với SSL cho Gemini
        self.gemini_http_client = httpx.Client(
            verify=str(Config.CERT)
        )

        # Thiết lập HTTP client cho GitHub (nếu bạn cần bỏ qua verify hoặc dùng cert riêng)
        self.github_http_client = httpx.Client(
            verify=False
        )

    def create_groq_model(self):
        return ChatGroq(
            model=Config.GROQ_MODEL_NAME,
            groq_api_key=Config.GROQ_API_KEY,
            temperature=0,
            http_client=self.groq_http_client
        )
    
    def create_gemini_model(self):
        return ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL_NAME,
            api_key=Config.GEMINI_API_KEY,
            client_args={
                "http_client": self.gemini_http_client
            }
        )
    
    def create_gpt_model(self):
        return ChatOpenAI(
            model=Config.GPT_MODEL_NAME,
            api_key=Config.GITHUB_KEY,
            base_url=Config.GITHUB_ENDPOINT,
            http_client=self.github_http_client,
            temperature=0
        )
    
    def get_gpt_model(self):
        return self.create_gpt_model()
    
    def get_groq_model(self):
        return self.create_groq_model()
    
    def get_gemini_model(self):
        return self.create_gemini_model()