import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME")

    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME")

    # DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "databases", "documents")
    # DB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "databases", "spider2-localdb")
    # DB_KNOWLEDGE_MAPPING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "databases", "db_knowledge.json")
    # # CERT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_cert.pem")
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # CERT = os.path.join(BASE_DIR, "company_cert.pem")
    BASE_DIR = Path(__file__).resolve().parent.parent

    CERT = BASE_DIR / "company_cert.pem"
    DB_ROOT = BASE_DIR / "resource" / "databases" / "spider2-localdb"
    DB_KNOWLEDGE_MAPPING = BASE_DIR / "resource" / "databases" / "db_knowledge.json"
    DOC_ROOT = BASE_DIR / "resource" / "databases" / "documents"
    
    