"""MeetingMind · 会议分析页"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import streamlit as st
from cloud_config import get_config_value
from utils import apply_css, parse_participants, render_plan, render_tasks, render_todos, todos_to_json, todos_to_md


st.set_page_config(page_title="会议分析 · MeetingMind", page_icon="📋", layout="wide", initial_sidebar_state="expanded")
apply_css()

with st.sidebar:
    if st.button("← 首页", key="back_home"):
        st.switch_page("demo_ui.py")
    st.markdown('<hr style="border-color:#292524;margin:12px 0;">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#78716C;margin:8px 0 16px;">CONFIGURATION</p>', unsafe_allow_html=True)
    default_api_key = get_config_value("OPENAI_API_KEY", "")
    default_base_url = get_config_value("OPENAI_BASE_URL", "https://api.deepseek.com")
    default_model = get_config_value("OPENAI_MODEL", "deepseek-chat")
    api_key = st.text_input("API Key", type="password", value=default_api_key, placeholder="sk-...")
    base_url = st.text_input("Base URL", value=default_base_url)
    model_name = st.text_input("Model", value=default_model)
    if not api_key.strip():
        st.info("Streamlit Cloud 可在 App settings → Secrets 中配置 OPENAI_API_KEY。")
    st.markdown('<hr style="border-color:#292524;margin:16px 0;">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;color:#57534E;">v0.5 · prototype</p>', unsafe_allow_html=True)

st.markdown(
    '<div style="display:flex;align-items:baseline;gap:14px;margin-bottom:4px;">'
    '<span style="font-family:Outfit,sans-serif;font-weight:700;font-size:26px;color:#1A1917;letter-spacing:-0.5px;">'
    'Meeting<span style="color:#DC2626;">Mind</span></span>'
    '<span style="font-size:13px;color:#78716C;">会议纪要 → 结构化行动计划</span></div>'
    '<div style="height:1px;background:#E5E3DE;margin:14px 0 24px;"></div>',
    unsafe_allow_html=True)

DEMO_TXT = """这周我们要把支付功能上线。
李四：后端支付接口我周三前完成。
张三：前端这边等接口好了再接入支付页面。
王五：测试这边等前后端联调完成后做回归测试。
另外上线之前需要产品确认一下支付流程，张三你和产品那边对一下。
还有服务器需要提前准备一下，运维这边安排一下。"""
DEMO_PPL = "张三/前端开发\n李四/后端开发\n王五/测试工程师"

def _input_block():
    # ── 文件上传 or 手动输入切换 ──────────────────────────────────────────
    upload_tab, manual_tab = st.tabs(["📁 上传文件", "✏️ 手动输入"])

    with upload_tab:
        fu_col, fp_col = st.columns([3, 1])
        with fu_col:
            st.markdown('<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#78716C;margin-bottom:6px;">会议内容文件</p>', unsafe_allow_html=True)
            meeting_file = st.file_uploader("", type=["txt","md"], key="meeting_file_up", label_visibility="collapsed")
            if meeting_file:
                content = meeting_file.read().decode("utf-8", errors="ignore")
                st.session_state["mi"] = content
                st.success(f"已读取：{meeting_file.name}（{len(content)} 字符）")
        with fp_col:
            st.markdown('<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#78716C;margin-bottom:6px;">参与者文件</p><p style="font-size:11px;color:#A8A29E;margin-bottom:6px;">每行：姓名/角色</p>', unsafe_allow_html=True)
            people_file = st.file_uploader("", type=["txt","md"], key="people_file_up", label_visibility="collapsed")
            if people_file:
                content_p = people_file.read().decode("utf-8", errors="ignore")
                st.session_state["pi"] = content_p
                st.success(f"已读取：{people_file.name}")
        # 已加载的内容预览
        if st.session_state.get("mi"):
            st.markdown(f'<p style="font-size:12px;color:#78716C;margin-top:8px;">📄 会议内容已就绪（{len(st.session_state["mi"])} 字符）</p>', unsafe_allow_html=True)

    with manual_tab:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown('<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#78716C;margin-bottom:6px;">会议内容</p>', unsafe_allow_html=True)
            st.text_area("", height=180, label_visibility="collapsed", placeholder="粘贴会议记录...", key="mi")
        with c2:
            st.markdown('<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#78716C;margin-bottom:6px;">参与者</p><p style="font-size:11px;color:#A8A29E;margin-bottom:6px;">姓名/角色，每行一人</p>', unsafe_allow_html=True)
            st.text_area("", height=180, label_visibility="collapsed", placeholder="张三/前端开发\n李四/后端开发", key="pi")

    bc1, bc2, _ = st.columns([2, 1, 5])
    with bc1: rb = st.button("▶  开始分析", use_container_width=True, key="run_btn_main")
    with bc2: db = st.button("加载示例",   use_container_width=True, key="demo_btn_main")
    if db:
        st.session_state["mi"] = DEMO_TXT
        st.session_state["pi"] = DEMO_PPL
        st.rerun()
    return rb

have_result = bool(st.session_state.get("meeting_plan"))
if have_result:
    with st.expander("🔄 重新分析", expanded=False):
        run_btn = _input_block()
else:
    run_btn = _input_block()

if run_btn:
    txt = st.session_state.get("mi", "")
    pr  = st.session_state.get("pi", "")
    if not txt.strip(): st.warning("请输入会议内容。"); st.stop()
    if not api_key.strip(): st.warning("请在侧边栏填入 API Key。"); st.stop()
    os.environ["OPENAI_API_KEY"]  = api_key
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["OPENAI_MODEL"]    = model_name
    parts = parse_participants(pr)
    from app.prototype.meeting_pipeline import run_pipeline
    with st.spinner("正在分析会议内容..."):
        try:
            result = run_pipeline(txt, parts)
        except Exception as e:
            st.error(f"分析失败：{e}"); st.stop()
    # 持久化到 session_state，返回页面后仍可复现
    st.session_state["meeting_tasks"] = result.get("tasks", [])
    st.session_state["meeting_plan"]  = result.get("execution_plan", [])
    st.session_state["meeting_todos"] = result.get("personal_todos", {})
    st.session_state["last_todos"]    = result.get("personal_todos", {})
    st.session_state["last_tasks"]    = result.get("tasks", [])
    st.rerun()  # 触发重渲染，使输入区折叠

# ── 渲染结果（run_btn 触发 或 session_state 有缓存时都展示）──────────────────
if st.session_state.get("meeting_plan"):
    tasks = st.session_state["meeting_tasks"]
    plan  = st.session_state["meeting_plan"]
    todos = st.session_state["meeting_todos"]
    nm   = sum(1 for s in plan if s.get("track") == "main")
    np2  = len(plan) - nm
    nb   = sum(1 for t in tasks if t.get("is_blocker"))
    nppl = len([k for k in todos if k != "未分配"])
    st.markdown(
        f'<div style="display:flex;gap:28px;flex-wrap:wrap;padding:16px 0;border-top:1px solid #E5E3DE;'
        f'border-bottom:1px solid #E5E3DE;margin:20px 0 28px;">'
        + "".join(
            f'<div style="display:flex;flex-direction:column;gap:2px;">'
            f'<span style="font-size:11px;color:#78716C;letter-spacing:0.04em;">{l}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:24px;font-weight:700;color:#1A1917;line-height:1;">{v}</span></div>'
            for v, l in [(len(tasks),"任务总数"),(nm,"主流程步骤"),(np2,"并行任务"),(nb,"关键阻塞"),(nppl,"涉及人员")])
        + '</div>', unsafe_allow_html=True)
    # Execution Plan hero
    st.markdown(
        '<div style="margin-bottom:8px;">'
        '<span style="font-size:18px;font-weight:700;color:#1A1917;font-family:Outfit,sans-serif;">执行计划</span>'
        '<span style="font-size:13px;color:#78716C;margin-left:12px;">Execution Plan</span></div>'
        '<div style="height:2px;background:#1A1917;width:40px;margin-bottom:20px;"></div>',
        unsafe_allow_html=True)
    render_plan(plan)
    st.markdown('<div style="height:1px;background:#E5E3DE;margin:32px 0 24px;"></div>', unsafe_allow_html=True)
    # Detail tabs
    tab_tasks, tab_todos, tab_dl = st.tabs(["任务详情", "个人待办", "📥 下载"])
    with tab_tasks: render_tasks(tasks)
    with tab_todos: render_todos(todos)
    with tab_dl:
        st.markdown('<p style="font-size:13px;color:#78716C;margin-bottom:20px;">按人下载任务清单，可直接导入工作模式。</p>', unsafe_allow_html=True)
        people = [p for p in todos if p != "未分配"]
        dl_cols = st.columns(min(len(people), 4)) if people else []
        for i, person in enumerate(people):
            with dl_cols[i % 4]:
                st.markdown(f'<p style="font-size:13px;font-weight:600;color:#1A1917;margin-bottom:8px;">{person}</p>', unsafe_allow_html=True)
                person_todos = {person: todos[person]}
                st.download_button(
                    label="JSON",
                    data=todos_to_json(person_todos),
                    file_name=f"todolist_{person}.json",
                    mime="application/json",
                    key=f"dl_json_{person}",
                    use_container_width=True)
                st.download_button(
                    label="Markdown",
                    data=todos_to_md(person_todos, tasks),
                    file_name=f"todolist_{person}.md",
                    mime="text/markdown",
                    key=f"dl_md_{person}",
                    use_container_width=True)
        st.markdown('<hr style="border-color:#E5E3DE;margin:20px 0;">', unsafe_allow_html=True)
        st.download_button(
            label="📥 下载全部（JSON）",
            data=todos_to_json(todos),
            file_name="todolist_all.json",
            mime="application/json",
            key="dl_all_json",
            use_container_width=False)
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        if st.button("→ 进入工作模式", key="go_work_from_meeting"):
            st.switch_page("pages/2_工作模式.py")
