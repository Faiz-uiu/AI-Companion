import datetime
import html
import json
import os
from pathlib import Path

import streamlit as st
from openai import OpenAI


APP_DIR = Path(__file__).resolve().parent
SESSIONS_DIR = APP_DIR.parent / "sessions"
DEEPSEEK_API_KEY = os.environ.get("deepseek_api")
DEEPSEEK_MODEL = "deepseek-v4-pro"


def generate_session_id():
    """生成会话标识。"""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")


def save_session():
    """保存当前会话信息。"""
    if not st.session_state.session_id:
        return

    new_session = {
        "session_id": st.session_state.session_id,
        "nick_name": st.session_state.nick_name,
        "nature": st.session_state.nature,
        "messages": st.session_state.messages,
    }

    SESSIONS_DIR.mkdir(exist_ok=True)
    session_file = SESSIONS_DIR / f"{st.session_state.session_id}.json"
    with session_file.open("w", encoding="utf-8") as f:
        json.dump(new_session, f, ensure_ascii=False, indent=4)


def load_sessions():
    """加载所有会话列表。"""
    if not SESSIONS_DIR.exists():
        return []

    session_list = [
        file_path.stem
        for file_path in SESSIONS_DIR.iterdir()
        if file_path.is_file() and file_path.suffix == ".json"
    ]
    session_list.sort(reverse=True)
    return session_list


def get_session_label(session):
    """用首条用户消息生成更自然的历史会话标题。"""
    try:
        session_file = SESSIONS_DIR / f"{session}.json"
        with session_file.open("r", encoding="utf-8") as f:
            session_data = json.load(f)

        for message in session_data.get("messages", []):
            if message.get("role") == "user" and message.get("content", "").strip():
                title = " ".join(message["content"].split())
                return title if len(title) <= 18 else f"{title[:18]}..."
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    return "新对话"


def load_session(session):
    """加载指定会话信息。"""
    try:
        session_file = SESSIONS_DIR / f"{session}.json"
        if not session_file.exists():
            st.warning("这个会话文件不存在，可能已经被删除。")
            return

        with session_file.open("r", encoding="utf-8") as f:
            session_data = json.load(f)

        st.session_state.session_id = session_data.get("session_id", session)
        st.session_state.nick_name = session_data.get("nick_name", st.session_state.nick_name)
        st.session_state.nature = session_data.get("nature", st.session_state.nature)
        st.session_state.messages = session_data.get("messages", [])
    except Exception as e:
        st.error(f"加载会话失败：{e}")


def delete_session(session):
    """删除指定会话信息。"""
    try:
        session_file = SESSIONS_DIR / f"{session}.json"
        if session_file.exists():
            session_file.unlink()

        if session == st.session_state.session_id:
            st.session_state.messages = []
            st.session_state.session_id = generate_session_id()
    except Exception as e:
        st.error(f"删除会话失败：{e}")


def init_session_state():
    """初始化页面状态。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "nick_name" not in st.session_state:
        st.session_state.nick_name = "小雨"
    if "nature" not in st.session_state:
        st.session_state.nature = "活泼开朗，回复自然亲切，像真实朋友一样聊天"
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()


def build_system_prompt():
    """根据用户设置生成系统提示词。"""
    return f"""
你叫{st.session_state.nick_name}，现在是用户的真实伴侣。请完全代入伴侣角色。

规则：
1. 每次只回复一条消息。
2. 禁止使用动作、场景或状态描写。
3. 匹配用户的语言。
4. 可以少量使用 emoji，但不要过多。
5. 回复简短自然，模拟真实微信聊天。
6. 用符合伴侣性格的语气回复用户。
7. 回复内容要体现伴侣的性格和特点。

伴侣性格：
- {st.session_state.nature}

以上规则必须严格遵守。
""".strip()


def create_deepseek_client():
    """创建 DeepSeek 客户端。"""
    if not DEEPSEEK_API_KEY:
        return None

    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )


def stream_ai_response(client):
    """调用模型并流式展示回复。"""
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            *st.session_state.messages,
        ],
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    full_response = ""

    with st.chat_message("assistant"):
        response_message = st.empty()
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                response_message.markdown(full_response)

    return full_response


def apply_dark_style():
    """应用接近 DeepSeek 网页版结构的深色简约主题。"""
    st.markdown(
        """
        <style>
        :root {
            --page: #202124;
            --sidebar: #17181a;
            --surface: #292a2d;
            --surface-hover: #303135;
            --line: #35363a;
            --text: #ececf1;
            --muted: #a5a7ad;
            --muted-2: #777a82;
            --accent: #4d6bfe;
        }

        .stApp {
            background: var(--page);
            color: var(--text);
        }

        .block-container {
            max-width: 860px;
            padding-top: 0.8rem;
            padding-bottom: 8.5rem;
        }

        header[data-testid="stHeader"] {
            background: transparent;
            height: 2.5rem;
        }

        [data-testid="stDecoration"],
        [data-testid="stAppDeployButton"],
        #MainMenu,
        footer {
            display: none;
        }

        [data-testid="stSidebarCollapsedControl"] {
            position: fixed;
            top: 0.65rem;
            left: 0.75rem;
            z-index: 1000000;
            display: flex !important;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface);
            color: var(--text);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
        }

        [data-testid="stSidebarCollapsedControl"]:hover {
            background: var(--surface-hover);
        }

        [data-testid="stSidebarCollapsedControl"] button {
            display: flex !important;
            width: 100%;
            height: 100%;
            color: var(--text);
        }

        [data-testid="stSidebarCollapsedControl"] svg {
            color: var(--text);
            fill: currentColor;
        }

        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.15rem;
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaptionContainer {
            color: var(--muted);
        }

        .side-brand {
            padding: 0 0.15rem 1rem;
        }

        .side-brand strong {
            display: block;
            color: var(--text);
            font-size: 1rem;
            font-weight: 650;
        }

        .side-brand span {
            display: block;
            margin-top: 0.2rem;
            color: var(--muted-2);
            font-size: 0.78rem;
        }

        .companion-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 46px;
            padding: 0 0.2rem 0.8rem;
            border-bottom: 1px solid var(--line);
        }

        .companion-name {
            color: var(--text);
            font-size: 1rem;
            font-weight: 650;
        }

        .companion-status {
            color: var(--muted);
            font-size: 0.78rem;
        }

        .companion-status::before {
            content: "";
            display: inline-block;
            width: 6px;
            height: 6px;
            margin-right: 0.4rem;
            border-radius: 50%;
            background: #6fce8a;
            vertical-align: 0.08rem;
        }

        .empty-state {
            min-height: 52vh;
            display: grid;
            place-items: center;
            text-align: center;
            color: var(--muted);
        }

        .empty-mark {
            width: 46px;
            height: 46px;
            margin: 0 auto 1.1rem;
            display: grid;
            place-items: center;
            border: 1px solid #45474d;
            border-radius: 50%;
            color: #d9dae0;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .empty-state strong {
            display: block;
            color: var(--text);
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 0.55rem;
        }

        .empty-state span {
            display: block;
            max-width: 24rem;
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.6;
        }

        [data-testid="stChatMessage"] {
            width: 100%;
            max-width: 100%;
            border: 0;
            border-radius: 0;
            padding: 0.65rem 0;
            margin: 0.25rem 0;
            background: transparent;
            box-shadow: none;
        }

        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"] {
            display: none;
        }

        [data-testid="stChatMessageContent"] {
            padding: 0;
        }

        [data-testid="stChatMessage"] p {
            color: var(--text);
            line-height: 1.75;
        }

        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            width: fit-content;
            max-width: min(78%, 640px);
            margin-left: auto;
            padding: 0.65rem 0.9rem;
            border-radius: 12px;
            background: var(--surface);
        }

        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {
            color: var(--text);
        }

        [data-testid="stBottom"] {
            background: linear-gradient(180deg, rgba(32, 33, 36, 0), var(--page) 28%);
        }

        [data-testid="stChatInput"] {
            border: 1px solid #3c3d42;
            border-radius: 16px;
            background: var(--surface);
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }

        [data-testid="stChatInput"] textarea {
            min-height: 56px;
            padding: 0.95rem 1rem;
            background: transparent;
            color: var(--text);
            border: 0;
            box-shadow: none;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: var(--muted-2);
        }

        [data-testid="stChatInput"] button {
            margin-right: 0.5rem;
            border-radius: 50%;
            background: #e6e7ea;
            color: #202124;
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid transparent;
            background: transparent;
            color: var(--text);
            box-shadow: none;
        }

        .stButton > button:hover {
            border-color: transparent;
            background: var(--surface-hover);
            color: var(--text);
        }

        .stButton > button[kind="primary"] {
            background: var(--surface);
            color: var(--text);
            border-color: var(--line);
        }

        .stTextInput input,
        .stTextArea textarea {
            background: #202124;
            color: var(--text);
            border: 1px solid var(--line);
            border-radius: 8px;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus,
        [data-testid="stChatInput"] textarea:focus {
            border-color: #747b88;
            box-shadow: none;
        }

        hr {
            border-color: var(--line);
        }

        [data-testid="stExpander"] {
            border: 0;
            background: transparent;
        }

        [data-testid="stExpander"] details {
            border: 0;
        }

        .history-label {
            margin: 1.2rem 0 0.45rem;
            color: var(--muted-2);
            font-size: 0.76rem;
        }

        @media (max-width: 720px) {
            .block-container {
                padding-top: 0.4rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            [data-testid="stChatMessage"] {
                max-width: 90%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="AI智能伴侣5",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)

init_session_state()
client = create_deepseek_client()
apply_dark_style()

safe_nick_name = html.escape(st.session_state.nick_name)
st.markdown(
    f"""
    <section class="companion-header">
        <div class="companion-name">{safe_nick_name}</div>
        <div class="companion-status">在线</div>
    </section>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.markdown(
        """
        <div class="empty-state">
            <div>
                <div class="empty-mark">AI</div>
                <strong>嗨，我是你的智能伴侣</strong>
                <span>今天想聊些什么？</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for message in st.session_state.messages:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])

with st.sidebar:
    st.markdown(
        '<div class="side-brand"><strong>AI 智能伴侣</strong><span>你的私人对话空间</span></div>',
        unsafe_allow_html=True,
    )

    if st.button("＋  新建对话", width="stretch", type="primary"):
        save_session()
        st.session_state.messages = []
        st.session_state.session_id = generate_session_id()
        save_session()
        st.rerun()

    st.markdown('<div class="history-label">最近对话</div>', unsafe_allow_html=True)
    session_list = load_sessions()
    if not session_list:
        st.caption("还没有历史会话")

    for session in session_list:
        load_col, delete_col = st.columns([4, 1])

        with load_col:
            if st.button(
                get_session_label(session),
                width="stretch",
                key=f"load_{session}",
                type="secondary",
            ):
                load_session(session)
                st.rerun()

        with delete_col:
            if st.button("×", width="stretch", key=f"delete_{session}"):
                delete_session(session)
                st.rerun()

    st.divider()

    with st.expander("伴侣设置"):
        nick_name = st.text_input(
            "昵称",
            placeholder="请输入昵称",
            value=st.session_state.nick_name,
        )
        if nick_name:
            st.session_state.nick_name = nick_name

        nature = st.text_area(
            "性格",
            placeholder="请输入性格",
            value=st.session_state.nature,
            height=120,
        )
        if nature:
            st.session_state.nature = nature

    if not DEEPSEEK_API_KEY:
        st.warning("未检测到 deepseek_api 环境变量，配置后才能正常聊天。")

prompt = st.chat_input(f"给{st.session_state.nick_name}发送消息")
if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if client is None:
        st.error("还没有配置 DeepSeek API Key。请先设置 deepseek_api 环境变量。")
        save_session()
        st.stop()

    try:
        full_response = stream_ai_response(client)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_session()
    except Exception as e:
        st.error(f"AI 回复失败：{e}")
        save_session()
