import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    # GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    # API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME")

    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME")

    # DB_ROOT = os.getenv("DB_ROOT_PATH")
    # DOC_ROOT = os.getenv("DOC_ROOT_PATH")
    DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "databases", "documents")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_ROOT = os.path.join(BASE_DIR, "resource", "databases", "spider2-localdb")
    