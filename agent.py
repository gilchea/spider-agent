from langchain_groq import ChatGroq
from config import Config
import os
from langchain.agents import create_agent
from prompts import SQL_GENERATION_PROMPT
import json
from tools import create_db_tools
from database import DatabaseManager
# from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.middleware.model_fallback import ModelFallbackMiddleware
# import google.generativeai as genai
import ssl

BASE_DIR = os.path.dirname(__file__)
cert_path = os.path.join(BASE_DIR, "company_cert.pem")

# ✅ QUAN TRỌNG
os.environ["SSL_CERT_FILE"] = cert_path
os.environ["REQUESTS_CA_BUNDLE"] = cert_path

print("Using cert:", cert_path)

ssl._create_default_https_context = ssl.create_default_context(
    cafile=cert_path
)

def get_local_instances(file_path: str):
    """Lọc các item có instance_id bắt đầu bằng 'local'."""
    local_items = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            if str(item.get("instance_id", "")).startswith("local"):
                local_items.append(item)
    return local_items
    
def create_nl2sql_agent(db_id: str):
    # Tạo instance DatabaseManager cho db_id cụ thể
    db_manager = DatabaseManager(db_id)
    
    # Định nghĩa system prompt với hướng dẫn chi tiết cho agent khi làm việc với cơ sở dữ liệu
    SYSTEM_PROMPT = """
    Bạn là một Chuyên gia Phân tích Dữ liệu SQL (SQLite Expert). 
    Nhiệm vụ của bạn là chuyển đổi câu hỏi từ người dùng thành câu lệnh SQL chính xác và thực thi nó để trả về kết quả.
    
    CÁC CÔNG CỤ BẠN CÓ
    - `list_tables`: dùng khi bạn chưa biết database có những bảng nào
    - `get_schemas`: dùng khi cần biết cấu trúc bảng (cột, kiểu dữ liệu)
    - `get_external_knowledge`: dùng khi cần hiểu thêm business logic
    - `check_syntax`: dùng để kiểm tra tính hợp lệ của SQL
    - `execute_sql`: dùng để thực thi SQL và lấy kết quả

    Kiển thức để tạo SQL tốt:
    1. Hiểu câu hỏi của người dùng
    1. hiểu được schema của database 
    2. Hiểu được quy trình nghiệp vụ 'External Knowledge File'
    3. Xác định các bảng liên quan và điều kiện lọc, join, aggregation
    4. Viết SQL dựa trên schema thực tế, tránh đoán

    QUY TẮC
    - Luôn ưu tiên hiểu schema trước khi viết SQL
    - Gọi `get_external_knowledge` khi thực sự cần hiểu business logic, không lạm dụng
    - Không bao giờ đoán schema, chỉ dựa trên thông tin thực tế từ `get_schemas`
    - Chỉ lấy schema của các bảng liên quan đến câu hỏi, không lấy tất cả
    - Kiểm tra syntax trước khi thực thi
    - Chỉ read-only (SELECT)
    - Chỉ thêm LIMIT khi truy vấn danh sách và không có yêu cầu cụ thể
    - Dừng lại sau khi có kết quả

    FORMAT SUY NGHĨ

    Thought → Action → Observation
    """

    model_groq = ChatGroq(
            model=Config.GROQ_MODEL_NAME,
            groq_api_key=Config.GROQ_API_KEY,
            temperature=0 )
    
    model_qwen = ChatGoogleGenerativeAI(model=Config.QWEN_MODEL_NAME, google_api_key=Config.QWEN_API_KEY)
    
    model_gemini = ChatGoogleGenerativeAI(model=Config.GEMINI_MODEL_NAME, google_api_key=Config.GEMINI_API_KEY)

    agent = create_agent(
        model=model_qwen,
        tools=create_db_tools(db_id),
        system_prompt=SYSTEM_PROMPT,
        middleware= [ModelFallbackMiddleware(
            model_groq, model_gemini
        )]
    )
    return agent


