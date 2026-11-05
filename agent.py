#!/usr/bin/env python
# coding: utf-8
import os
import csv
from openai import OpenAI
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com"
)
def load_courses_from_csv():
    """读取课表.csv，返回 {课程名: [时间+教室, ...]}"""
    courses = {}
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "课表.csv")
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["课程名"].strip()
            time = row["上课时间"].strip()
            room = row["教室"].strip()
            if name not in courses:
                courses[name] = []
            courses[name].append(f"{time} {room}")
    return courses
courses_from_csv = load_courses_from_csv()
# 课程表和教师数据
teacher_data = {
    "聂老师": {"地点": "办公楼201", "答疑时间": "周四下午2-4点"},
    "刘老师":{"地点":"办公楼202","答疑时间":"周一晚上18-21点"}
}
# 工具1：查课程时间
def query_course_time(course_name):
    # 模糊匹配：不管带不带"课"字都能查到
    for name, info_list in courses_from_csv.items():
        if name in course_name or course_name in name:
            return "；".join(info_list)
    return "没找到这门课"
# 工具2：查教师办公室
def query_teacher_office(teacher_name):
    if teacher_name in teacher_data:
        return f"{teacher_name}：办公室在{teacher_data[teacher_name]['地点']}，答疑时间{teacher_data[teacher_name]['答疑时间']}"
    else:
        return "没找到这位老师"
# 工具3：算总学时
def calc_credit_hours(per_week, weeks):
    total = per_week * weeks
    return f"每周{per_week}学时，共{weeks}周，总学时{total}学时"
import re
tools_info = """
你有三个工具可以用：
1. query_course_time：查课程时间和教室，参数是课程名
2. query_teacher_office：查教师办公室和答疑时间，参数是教师姓名
3. calc_credit_hours：算总学时，参数是每周学时和周数

如果需要调用工具，只输出一行，格式参考这些例子：
【调用工具】query_course_time|数据标注
【调用工具】query_teacher_office|聂老师
【调用工具】calc_credit_hours|4,16

注意：工具名必须是上面的真实名字，参数必须是具体值，
不要输出"工具名"、"参数1"这些占位文字。
不需要调用工具就直接回答。
"""
def parse_tool_call(response):
    """从模型输出中解析工具名和参数"""
    match = re.search(r'【调用工具】(.*?)\|(.*)', response)
    if match:
        tool_name = match.group(1).strip()
        params = [p.strip() for p in match.group(2).split(",")]
        params = [re.sub(r'^(课程名|教师姓名|课程|教师|每周学时|周数)[:：]?\s*', '', p) for p in params]
        return tool_name, params
    return None, None

def run_agent(question, max_rounds=5):
    messages = [
        {"role": "system", "content": "你是一个学校问答助手。" + tools_info},
        {"role": "user", "content": question}
    ]

    for i in range(max_rounds):
        # 把对话发给模型
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=100
        )
        response = resp.choices[0].message.content
        print(f"--- 模型第{i+1}轮输出 ---")
        print(response)
        # 解析要不要调工具
        tool_name, params = parse_tool_call(response)
        if tool_name is None:
            print("=== 最终回答 ===")
            print(response)
            return response
        # 执行工具
        if tool_name == "query_course_time":
            result = query_course_time(params[0])
        elif tool_name == "query_teacher_office":
            result = query_teacher_office(params[0])
        elif tool_name == "calc_credit_hours":
            result = calc_credit_hours(int(params[0]), int(params[1]))
        else:
            result = "未知工具"
        print(f"调用工具: {tool_name}, 返回: {result}")
        # 把结果回灌给模型
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"工具返回结果: {result}，请根据结果回答用户的问题。"})
# ===== 智能体记忆模块 =====
memory = {}   # 记忆库：存 {问题: 答案}
def remember(question, answer):
    """记住：把问题+答案存进记忆库"""
    memory[question] = answer
    print("【记忆】已保存：", question)
def recall(question):
    """回忆：查记忆库里有没有问过同样的问题"""
    if question in memory:
        print("【记忆命中】不用再算，直接返回上次答案")
        return memory[question]
    return None
def run_agent_with_memory(question):
    """带记忆的智能体：先回忆，再回答，最后记住"""
    cached = recall(question)          # 1. 先查记忆
    if cached:
        return cached                 # 2. 有就返回，不干活
    answer = run_agent(question)       # 3. 没有才调原来的主循环
    remember(question, answer)         # 4. 回答完存进记忆
    return answer
# ===== 多智能体协作 =====
# 3个子智能体 + 1个调度主智能体
def course_agent(course_name):
    """子智能体1：查课程"""
    print("【课程智能体】收到任务：查", course_name)
    return query_course_time(course_name)
def teacher_agent(teacher_name):
    """子智能体2：查教师"""
    print("【教师智能体】收到任务：查", teacher_name)
    return query_teacher_office(teacher_name)
def calc_agent(hours, weeks):
    """子智能体3：算学时"""
    print("【计算智能体】收到任务：每周", hours, "学时 x", weeks, "周")
    return calc_credit_hours(hours, weeks)
def supervisor(task_type, *args):
    """主智能体：按任务类型分派给对应子智能体"""
    if task_type == "course":
        return course_agent(*args)
    elif task_type == "teacher":
        return teacher_agent(*args)
    elif task_type == "calc":
        return calc_agent(*args)
    return "未知任务类型"