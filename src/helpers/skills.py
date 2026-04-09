from typing import TypedDict

class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str  # Unique identifier for the skill
    description: str  # 1-2 sentence description to show in system prompt
    relevant_tables: list[str]  # List of tables relevant to the skill

SKILLS: list[Skill] = [
    {
        "name": "academic_scheduling",
        "description": "Quản lý Đào tạo & Lịch học. Dùng cho các câu hỏi về môn học, lớp học, phòng học, tòa nhà và lịch trình dạy/học.",
        "relevant_tables": [
            "Classes", "Subjects", "Class_Rooms", "Buildings", 
            "Categories", "Student_Schedules", "Faculty_Classes"
        ]
    },
    {
        "name": "hr_student_admin",
        "description": "Quản trị Nhân sự & Sinh viên. Dùng cho các câu hỏi về hồ sơ sinh viên, điểm GPA, thông tin giảng viên, lương, khoa, chuyên ngành và năng lực giảng dạy.",
        "relevant_tables": [
            "Students", "Staff", "Faculty", "Departments", "Majors", 
            "Faculty_Subjects", "Faculty_Categories", "Student_Class_Status", "Faculty_Classes"
        ]
    }
]

# SKILLS_CONFIG = {
#     "academic_scheduling": {
#         "description": "Quản lý Đào tạo & Lịch học. Dùng cho các câu hỏi về môn học, lớp học, phòng học, tòa nhà và lịch trình dạy/học.",
#         "relevant_tables": [
#             "Classes", "Subjects", "Class_Rooms", "Buildings", 
#             "Categories", "Student_Schedules", "Faculty_Classes"
#         ]
#     },
#     "hr_student_admin": {
#         "description": "Quản trị Nhân sự & Sinh viên. Dùng cho các câu hỏi về hồ sơ sinh viên, điểm GPA, thông tin giảng viên, lương, khoa, chuyên ngành và năng lực giảng dạy.",
#         "relevant_tables": [
#             "Students", "Staff", "Faculty", "Departments", "Majors", 
#             "Faculty_Subjects", "Faculty_Categories", "Student_Class_Status", "Faculty_Classes"
#         ]
#     }
# }