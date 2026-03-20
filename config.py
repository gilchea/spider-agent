import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    # GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    # API_KEY = os.getenv("GROQ_API_KEY")
    API_KEY = os.getenv("GOOGLE_API_KEY")

    MODEL_NAME = os.getenv("MODEL_NAME")
    # DB_ROOT = os.getenv("DB_ROOT_PATH")
    # DOC_ROOT = os.getenv("DOC_ROOT_PATH")
    DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "databases", "documents")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_ROOT = os.path.join(BASE_DIR, "resource", "databases", "spider2-localdb")
    
    # Cấu hình OpenRouter client
    # OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")