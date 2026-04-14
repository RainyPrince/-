import os
import time
import requests
from flask import Flask, render_template, request, session
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate

# -------------------------- 初始化配置（新增session支持） --------------------------
load_dotenv()
app = Flask(__name__)
# 必须配置secret_key，用于加密session（生产环境建议在.env中配置随机字符串）
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_123456")  # 开发环境临时密钥
# 配置session有效期（1小时，单位：秒）
app.config["PERMANENT_SESSION_LIFETIME"] = 3600

# 初始化通义AI客户端
try:
    text_client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    print(f"初始化通义文本客户端失败: {e}")
    text_client = None


# -------------------------- 会话记忆管理函数 --------------------------
def get_chat_history():
    """从session中读取历史对话，无则返回空列表"""
    # 历史对话格式：[{"role": "user", "content": "问题1"}, {"role": "assistant", "content": "回答1"}, ...]
    return session.get("chat_history", [])


def update_chat_history(user_question: str, ai_answer: str):
    """更新会话历史，最多保留10轮对话（避免上下文过长导致AI性能下降）"""
    chat_history = get_chat_history()
    # 添加当前轮对话
    chat_history.append({"role": "user", "content": user_question})
    chat_history.append({"role": "assistant", "content": ai_answer})
    # 保留最近10轮（即最后20条记录：每轮含用户+AI）
    session["chat_history"] = chat_history[-20:]
    # 标记session为"永久"（按配置的1小时有效期）
    session.permanent = True


def clear_chat_history():
    """清空会话历史"""
    session.pop("chat_history", None)


# -------------------------- 演示环境轻量限流 --------------------------
def is_rate_limited(limit_count: int = 8, window_seconds: int = 60):
    """
    基于 session 的轻量限流（默认每 60 秒最多 8 次提问）。
    返回: (是否限流, 剩余秒数)
    """
    now = int(time.time())
    hit_timestamps = session.get("rate_limit_hits", [])

    # 仅保留窗口期内的请求时间戳
    hit_timestamps = [ts for ts in hit_timestamps if now - ts < window_seconds]

    if len(hit_timestamps) >= limit_count:
        retry_after = window_seconds - (now - hit_timestamps[0])
        session["rate_limit_hits"] = hit_timestamps
        return True, max(retry_after, 1)

    hit_timestamps.append(now)
    session["rate_limit_hits"] = hit_timestamps
    return False, 0


# -------------------------- 提示词模板（支持历史对话上下文） --------------------------
legal_prompt = PromptTemplate(
    input_variables=["chat_history", "new_question"],  # 新增历史对话参数
    template="""
    你是专业的法律顾问，需基于中国现行有效的法律法规回答用户问题，且必须结合历史对话上下文：
    1. 历史对话参考：{chat_history}（理解用户之前的问题，避免重复回答）
    2. 用户当前问题：{new_question}
    3. 回答要求：
       - 必须引用具体法律依据（如《民法典》第XX条），禁止模糊表述；
       - 若当前问题是上一轮的追问（如“需要准备什么证据”），必须关联历史问题回答；
       - 结构清晰：先结论，再分点说明法律依据+操作建议；
       - 涉及个案细节时，必须提示“本回答仅为科普，具体需咨询执业律师”；
       - 严禁编造法条或引用过时内容。
    """
)


# -------------------------- 核心函数（传入历史对话） --------------------------
def legal_chain(new_question: str, chat_history: list):
    """结合历史对话，调用AI生成回答"""
    if not text_client:
        return "通义API客户端未初始化，请检查配置"

    try:
        # 格式化历史对话（转为字符串，便于AI理解）
        history_str = "\n".join([
            f"{'用户' if msg['role'] == 'user' else '系统'}：{msg['content'][:150]}..."  # 截取前150字，避免过长
            for msg in chat_history
        ]) if chat_history else "无历史对话"

        # 生成提示词
        prompt = legal_prompt.format(
            chat_history=history_str,
            new_question=new_question
        )

        # 调用AI（messages参数天然支持上下文，可直接传入历史对话）
        messages = [
            {"role": "system", "content": "你是严格依据中国法律的专业法律顾问，必须关联历史对话回答"},
            *chat_history,  # 直接传入历史对话列表，AI会自动理解上下文
            {"role": "user", "content": new_question}
        ]

        response = text_client.chat.completions.create(
            model="qwen-plus",  # 推荐用qwen-max提升上下文理解能力
            messages=messages,
            temperature=0.2,  # 低温度保证回答严谨
            max_tokens=1200,
            response_format={"type": "text", "strict": True}
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        error_msg = f"处理法律问题时出错: {str(e)}"
        # 补充常见错误提示
        if "API key" in str(e):
            error_msg += "（可能是API密钥无效或过期）"
        elif "timeout" in str(e).lower():
            error_msg += "（网络超时，建议稍后重试）"
        return error_msg


# -------------------------- 主路由（支持历史对话传递） --------------------------
@app.route("/", methods=["GET", "POST"])
def legal_qa():
    question = ""
    answer = ""
    error = ""
    chat_history = get_chat_history()  # 读取历史对话

    if request.method == "POST":
        limited, retry_after = is_rate_limited()
        if limited:
            error = f"请求过于频繁，请在 {retry_after} 秒后重试"
            return render_template(
                "index.html",
                question="",
                answer="",
                error=error,
                chat_history=chat_history
            )

        # 获取用户输入
        question = request.form.get("question", "").strip()
        category = request.form.get("category", "").strip()

        # 输入校验
        if not question:
            error = "请输入您的法律问题（如：公司拖欠工资该如何维权？）"
        else:
            if not text_client:
                error = "通义API客户端未初始化，请检查密钥配置"
            else:
                # 补充法律类别提示（帮助AI聚焦）
                if category:
                    new_question = f"【法律类别：{category}】{question}"
                else:
                    new_question = question

                # 调用AI（传入历史对话）
                answer = legal_chain(new_question, chat_history)

                # 将模型错误转换为页面错误提示，避免前端“无响应”体验
                if answer.startswith("通义API客户端未初始化") or answer.startswith("处理法律问题时出错"):
                    app.logger.error("法律问答失败: %s", answer)
                    error = answer
                    answer = ""
                else:
                    # 更新历史对话（仅当回答无错误提示时）
                    update_chat_history(question, answer)
                    # 刷新历史对话（用于页面展示）
                    chat_history = get_chat_history()

    # 传递数据到前端（新增chat_history）
    return render_template(
        "index.html",
        question=question,
        answer=answer,
        error=error,
        chat_history=chat_history  # 历史对话传递到前端
    )


# -------------------------- 清空历史对话路由 --------------------------
@app.route("/clear_history", methods=["POST"])
def clear_history():
    clear_chat_history()
    # 清空后重定向到首页，显示成功提示
    return render_template(
        "index.html",
        error="✅ 历史对话已清空",
        chat_history=[]  # 传递空历史
    )


# -------------------------- 健康检查路由 --------------------------
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


# -------------------------- 运行Flask应用 --------------------------
if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))

    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        use_reloader=debug_mode
    )