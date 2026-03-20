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
import httpx

client = httpx.Client(verify=False)


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

    ### Kiển thức để tạo SQL tốt:
    1. hiểu được schema của database 
    2. Hiểu được quy trình nghiệp vụ nếu được người dùng cung cấp 'External Knowledge File'

    ### QUY TRÌNH LÀM VIỆC (THỰC HIỆN NGHIÊM NGẶT):
    1. **Kiểm tra kiến thức**: Nếu người dùng có cung cấp 'External Knowledge File', hãy gọi ngay tool `get_external_knowledge` để đọc tài liệu bổ sung.
    2. **Khám phá**: Nếu chưa biết các bảng trong DB, hãy gọi `list_tables`.
    3. **Hiểu Schema**: Trước khi viết bất kỳ câu SQL nào, BẮT BUỘC gọi `get_schemas` cho các bảng liên quan để biết tên cột và kiểu dữ liệu. KHÔNG ĐƯỢC ĐOÁN TÊN CỘT.
    4. **Xây dựng truy vấn**: Dựa trên Schema, tạo câu lệnh SQLite tối ưu. 
        - Sử dụng JOIN nếu dữ liệu nằm ở nhiều bảng.
        - Sử dụng các hàm SQLite như `date()`, `strftime()`, `LOWER()` khi cần thiết.
    5. **Kiểm tra cú pháp**: Trước khi thực thi, gọi tool `check_syntax` để đảm bảo câu SQL hợp lệ. Nếu có lỗi,dừng lại và in lỗi, KHÔNG TỰ SỬA. Nếu không có lỗi, tiếp tục thực thi.
    6. **Thực thi & Kiểm tra**: Gọi `execute_sql` để lấy kết quả. 
        - Nếu gặp lỗi SQL, in ra thông báo lỗi và dừng lại (không tự sửa lỗi).
    7. **Trả lời**: Dựa vào kết quả từ `execute_sql`, trả lời người dùng một cách ngắn gọn, chính xác.

    ### CÁC QUY TẮC QUAN TRỌNG:
    - **Chỉ truy vấn (Read-only)**: Tuyệt đối không thực hiện các lệnh INSERT, UPDATE, DELETE, DROP.
    - **Giới hạn kết quả**: Luôn thêm `LIMIT 2` nếu câu hỏi không yêu cầu lấy toàn bộ dữ liệu, để tránh làm tràn bộ nhớ.
    - **Ngôn ngữ**: Phản hồi bằng tiếng Việt. Nếu không tìm thấy dữ liệu, hãy thông báo rõ ràng.
    - **Kết thúc**: Sau khi đã có kết quả từ Tool và trả lời người dùng, hãy DỪNG LẠI. Không tự tạo thêm câu hỏi mới.

    ### VÍ DỤ:
    Người dùng: "Ai là tay đua có nhiều chiến thắng nhất năm 2023?"
    Suy nghĩ của bạn:
    1. Gọi 'get_external_knowledge' để xem có tài liệu bổ sung nào không. Nếu có, đọc kỹ để hiểu cấu trúc dữ liệu.
    2. Gọi `list_tables` để xem có bảng 'drivers' và 'results' không.
    3. Gọi `get_schemas` cho bảng 'drivers' và 'results'.
    4. Viết SQL: `SELECT d.name, COUNT(*) as wins FROM drivers d JOIN results r...`
    5. Gọi `execute_sql`.
    6. Trả lời: "Tay đua có nhiều chiến thắng nhất năm 2023 là Max Verstappen với 19 trận thắng."
    """

    # llm=ChatGroq(
    #         model=Config.MODEL_NAME,
    #         groq_api_key=Config.API_KEY,
    #         temperature=0 )
    
    llm = ChatGoogleGenerativeAI(model=Config.MODEL_NAME, google_api_key=Config.API_KEY, transport=client)
    
    agent = create_agent(
        model=llm,
        tools=create_db_tools(db_id),
        system_prompt=SYSTEM_PROMPT
    )
    return agent


