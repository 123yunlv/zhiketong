import streamlit as st
from agent import run_agent_with_memory, memory
st.title("🎓 智课通-校园智能问答助手")
st.write("这是一个基于智能体的校园问答助手，您可以使用它来查询校园课程问题。")
with st.sidebar:
    st.image("photo.png", caption="智课通", width=200)
    st.header("⚙️ 功能说明")
    st.write("可查询：课程时间、教师办公室、总学时")
    st.markdown("---")
    st.success("记忆功能已开启")
# 历史记录区
if "history" not in st.session_state:
    st.session_state.history = []
# 输入框 + 按钮
question = st.text_input("请输入你的问题")
if st.button("发送"):
    if question:
        # 调用智能体前，先判断这个问题有没有记忆
        if question in memory:
            status = "记忆命中，秒回"
        else:
            status = "新问题，调用工具查询"
        answer = run_agent_with_memory(question)
        # 把这一轮问答存进历史
        st.session_state.history.append(("我", question))
        st.session_state.history.append(("智课通", answer + "（" + status + "）"))
# 把历史显示出来
st.write("---")
for who, text in st.session_state.history:
    if who == "我":
        with st.chat_message("user"):
            st.write(text)
    else:
        with st.chat_message("assistant"):
            st.write(text)
