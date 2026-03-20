from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import create_nl2sql_agent
from database import DatabaseManager

app = FastAPI(title="NL2SQL API", version="1.0")

# Request schemas
class LoadDBRequest(BaseModel):
    db_id: str

class QueryRequest(BaseModel):
    db_id: str
    question: str

# In-memory store (simple) Lưu agent theo db_id
agents = {}

# API: Load DB
@app.post("/load_db")  # Endpoint để load database và tạo agent tương ứng
def load_database(req: LoadDBRequest):
    try:
        db = DatabaseManager(req.db_id) # Tạo instance DatabaseManager để kiểm tra và lấy thông tin database
        tables = db.get_table_names()

        agent = create_nl2sql_agent(req.db_id)
        agents[req.db_id] = agent # Lưu agent vào dictionary để sử dụng cho các truy vấn sau này

        return {
            "success": True,
            "db_id": req.db_id,
            "tables": tables
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) # Trả về lỗi nếu có vấn đề khi load database hoặc tạo agent


# API: Query
@app.post("/query") # Endpoint để nhận câu hỏi và trả về kết quả từ agent
def run_query(req: QueryRequest):
    try:
        if req.db_id not in agents: # Kiểm tra nếu agent cho db_id chưa tồn tại, trả về lỗi
            raise HTTPException(
                status_code=400,
                detail="Database chưa được load"
            )

        agent = agents[req.db_id]

        input_content = f"Database: {req.db_id}\n"
        input_content += f"Question: {req.question}"

        response = agent.invoke({
            "messages": [
                {"role": "user", "content": input_content}
            ]
        })

        output = response["messages"][-1].content

        return {
            "success": True,
            "output": output,
            "raw": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))