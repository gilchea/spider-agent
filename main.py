import json
from agent import create_nl2sql_agent
from tools import create_db_tools

def get_local_instances(file_path: str):
    """Lọc các item có instance_id bắt đầu bằng 'local'."""
    local_items = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            if str(item.get("instance_id", "")).startswith("local"):
                local_items.append(item)
    return local_items

def main():
    file_path = "spider2-lite.jsonl"
    local_tasks = get_local_instances(file_path)
    
    print(f"Tìm thấy {len(local_tasks)} tác vụ local.")

    # chạy 1 tác vụ để test
    local_tasks = local_tasks[:1]

    for task in local_tasks:
        print(f"\n--- Đang xử lý: {task['instance_id']} ---")
        
        # 1. Khởi tạo Tools cho DB tương ứng
        tools = create_db_tools(task['db'])
        
        # 2. Khởi tạo Agent
        agent = create_nl2sql_agent(
            db_id=task['db'],
            question=task['question'], 
            doc_name=task['external_knowledge'],
            tools=tools
        )
        
        # 3. Thực thi
        try:
            result = agent.invoke({
                "input": task['question']
            })
            print(f"Kết quả: {result['output']}")
        except Exception as e:
            print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()