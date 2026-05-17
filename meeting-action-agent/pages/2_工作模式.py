"""MeetingMind · 工作模式"""
import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import streamlit as st
from cloud_config import get_config_value, local_deploy_hint, local_only_features_enabled
from utils import apply_css, _PC

CAN_RUN_LOCAL_FEATURES = local_only_features_enabled()

st.set_page_config(page_title="工作模式 · MeetingMind", page_icon="💼", layout="wide", initial_sidebar_state="expanded")
apply_css()
st.markdown("""
<style>
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.msg-bubble{animation:fadeUp 0.18s ease forwards}
</style>""", unsafe_allow_html=True)

def _default_models():
    secret_key = get_config_value("OPENAI_API_KEY", "")
    secret_base = get_config_value("OPENAI_BASE_URL", "https://api.deepseek.com")
    secret_model = get_config_value("OPENAI_MODEL", "deepseek-chat")
    return [
        {"name": "文职/DeepSeek", "api_key": secret_key, "base_url": secret_base, "model": secret_model},
        {"name": "通用/Gemini", "api_key": "", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.0-flash"},
    ]

DEFAULT_MODELS = _default_models()
SKILL_TEMPLATES={
    "写作助手":"你擅长中文写作，帮助用户撰写、润色各类文档，语言简洁专业。",
    "代码审查":"你是资深工程师，帮助用户分析代码逻辑、发现潜在问题并给出改进建议。",
    "邮件起草":"你帮助用户起草专业邮件，语气得体，结构清晰。",
    "会议总结":"你帮助用户梳理会议要点，提炼关键结论与行动项。",
    "数据分析":"你帮助用户理解数据、解读指标，给出有洞察力的分析。",
}

def init_state():
    for k,v in [("work_models",DEFAULT_MODELS[:]),("work_model_idx",0),("work_messages",[]),
                ("work_selected_task",None),("work_skill",""),("work_done_tasks",set())]:
        if k not in st.session_state: st.session_state[k]=v
    if "work_todolist" not in st.session_state:
        st.session_state["work_todolist"]=st.session_state.get("last_todos",{})
    if "work_user" not in st.session_state:
        ppl=[p for p in st.session_state.get("work_todolist",{}) if p!="未分配"]
        st.session_state["work_user"]=ppl[0] if ppl else ""

init_state()
models=st.session_state["work_models"]
todolist=st.session_state["work_todolist"]
cur_user=st.session_state.get("work_user","")
user_tasks=todolist.get(cur_user,[]) if todolist else []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="padding:14px 4px 8px;"><span style="font-family:Outfit,sans-serif;font-weight:700;font-size:20px;color:#E7E5E4;">Meeting<span style="color:#DC2626;">Mind</span></span></div>',unsafe_allow_html=True)
    st.markdown('<hr style="border-color:#292524;margin:0 0 10px;">',unsafe_allow_html=True)

    # User selector
    ppl=[p for p in todolist if p!="未分配"] if todolist else []
    if ppl:
        idx0=ppl.index(cur_user) if cur_user in ppl else 0
        new_user=st.selectbox("👤 用户",ppl,index=idx0,key="wb_user")
        if new_user!=cur_user:
            st.session_state["work_user"]=new_user
            st.session_state["work_selected_task"]=None
            st.session_state["work_messages"]=[]
            st.rerun()
        cnt=len(todolist.get(new_user,[]))
        st.markdown(f'<div style="background:#292524;border-radius:3px;padding:8px 10px;margin:2px 0 8px;"><div style="font-size:13px;font-weight:600;color:#E7E5E4;">{new_user}</div><div style="font-size:11px;color:#57534E;margin-top:2px;">{cnt} 项待办</div></div>',unsafe_allow_html=True)

    # Model selector
    mnames=[m["name"] for m in models]
    cidx=st.selectbox("🤖 模型",range(len(mnames)),format_func=lambda i:mnames[i],index=st.session_state["work_model_idx"],key="wb_model")
    st.session_state["work_model_idx"]=cidx
    cur_m=models[cidx]
    st.markdown(f'<p style="font-family:JetBrains Mono,monospace;font-size:10px;color:#44403C;margin:-4px 0 8px;">{cur_m["model"]}</p>',unsafe_allow_html=True)
    st.markdown('<hr style="border-color:#292524;margin:4px 0 10px;">',unsafe_allow_html=True)

    # Todolist in sidebar
    if user_tasks:
        done_set=st.session_state.get("work_done_tasks",set())
        done_cnt=sum(1 for t in user_tasks if t.get("task_id") in done_set)
        st.markdown(f'<p style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#57534E;margin-bottom:6px;">📋 MY TASKS <span style="color:#16A34A;">{done_cnt}/{len(user_tasks)}</span></p>',unsafe_allow_html=True)
        for item in user_tasks:
            pri=item.get("priority","medium")
            pc=_PC.get(pri,"#78716C")
            tid=item.get("task_id","")
            is_sel=st.session_state["work_selected_task"]==tid
            is_done=tid in done_set
            lc="#16A34A" if is_done else (pc if is_sel else "#44403C")
            task_text=f'<s style="color:#57534E;">{item.get("task","")}</s>' if is_done else item.get("task","")
            name_color="#57534E" if is_done else ("#E7E5E4" if is_sel else "#A8A29E")
            fw="400" if is_done else ("600" if is_sel else "400")
            bg="#1A1917" if is_done else ("#292524" if is_sel else "transparent")
            st.markdown(
                f'<div style="border-left:2px solid {lc};padding:7px 10px;margin-bottom:2px;'
                f'background:{bg};border-radius:0 2px 2px 0;">'
                f'<div style="font-size:12px;font-weight:{fw};color:{name_color};line-height:1.3;margin-bottom:2px;">{task_text}</div>'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<span style="font-size:9px;font-weight:700;text-transform:uppercase;color:{"#57534E" if is_done else pc};">{"完成" if is_done else pri}</span>'
                f'<span style="font-size:9px;color:#57534E;">{item.get("deadline") or ""}</span>'
                f'</div></div>',unsafe_allow_html=True)
            # 按钮行：选择 + 完成
            b1,b2=st.columns([1,1])
            with b1:
                sel_label="✓ 进行中" if is_sel else ("查看" if is_done else "开始")
                if st.button(sel_label,key=f"sel_{tid}",use_container_width=True):
                    if not is_sel:
                        st.session_state["work_selected_task"]=tid
                        st.session_state["work_messages"]=[]
                    st.rerun()
            with b2:
                done_label="↩ 撤销" if is_done else "✅ 完成"
                if st.button(done_label,key=f"done_{tid}",use_container_width=True):
                    if is_done: done_set.discard(tid)
                    else:
                        done_set.add(tid)
                        if is_sel:  # 完成后自动取消选中
                            st.session_state["work_selected_task"]=None
                            st.session_state["work_messages"]=[]
                    st.session_state["work_done_tasks"]=done_set
                    st.rerun()
        st.markdown('<hr style="border-color:#292524;margin:8px 0;">',unsafe_allow_html=True)

    # Settings expander
    with st.expander("⚙ 设置"):
        st.markdown('<p style="font-size:10px;font-weight:600;letter-spacing:0.08em;color:#A8A29E;text-transform:uppercase;margin-bottom:4px;">Skill 模板</p>',unsafe_allow_html=True)
        sk=st.selectbox("",["不使用"]+list(SKILL_TEMPLATES.keys()),key="wb_sk",label_visibility="collapsed")
        st.session_state["work_skill"]=SKILL_TEMPLATES.get(sk,"")
        if sk!="不使用": st.caption(SKILL_TEMPLATES[sk])
        st.markdown('<p style="font-size:10px;font-weight:600;letter-spacing:0.08em;color:#A8A29E;text-transform:uppercase;margin:10px 0 4px;">模型配置</p>',unsafe_allow_html=True)
        for i,m in enumerate(models):
            with st.expander(m["name"]):
                m["name"]=st.text_input("显示名称",m["name"],key=f"mn{i}")
                m["api_key"]=st.text_input("API Key",m["api_key"],key=f"mk{i}",type="password")
                m["base_url"]=st.text_input("Base URL",m["base_url"],key=f"mb{i}")
                m["model"]=st.text_input("Model ID",m["model"],key=f"mm{i}")
        if st.button("+ 添加模型",key="add_m"): models.append({"name":"新模型","api_key":"","base_url":"","model":""}); st.rerun()
        st.markdown('<hr style="border-color:#292524;margin:6px 0;">',unsafe_allow_html=True)
        if not todolist:
            up=st.file_uploader("上传 Todolist JSON",type=["json"],key="sb_up")
            if up:
                try:
                    data=json.loads(up.read().decode("utf-8"))
                    st.session_state["work_todolist"]=data
                    ppl2=[p for p in data if p!="未分配"]
                    if ppl2: st.session_state["work_user"]=ppl2[0]
                    st.rerun()
                except Exception as e: st.error(f"解析失败：{e}")
            if st.session_state.get("last_todos"):
                if st.button("使用上次会议结果",key="use_last"): st.session_state["work_todolist"]=st.session_state["last_todos"]; st.rerun()
        else:
            if st.button("🗑 清除任务清单",key="clear_tl"):
                st.session_state["work_todolist"]={}
                st.session_state["work_selected_task"]=None
                st.session_state["work_messages"]=[]; st.rerun()
    st.markdown('<hr style="border-color:#292524;margin:6px 0;">',unsafe_allow_html=True)
    if st.button("← 首页",key="wk_home"): st.switch_page("demo_ui.py")

# ── Main: no todolist ─────────────────────────────────────────────────────────
if not todolist:
    st.markdown('<div style="text-align:center;padding:100px 0;animation:fadeIn 0.4s ease;"><div style="font-size:48px;margin-bottom:16px;">📂</div><p style="font-size:18px;font-weight:600;color:#1A1917;">请在左侧设置中上传任务清单</p></div>',unsafe_allow_html=True)
    st.stop()

# ── Main: no task selected ────────────────────────────────────────────────────
sel_id=st.session_state.get("work_selected_task")
sel_task=next((t for t in user_tasks if t.get("task_id")==sel_id),None)
cur_m=models[st.session_state["work_model_idx"]]

if not sel_task:
    st.markdown(
        '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:65vh;animation:fadeIn 0.4s;">'
        '<div style="width:64px;height:64px;background:#F1F0EE;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;margin-bottom:16px;">💬</div>'
        '<p style="font-size:16px;font-weight:600;color:#1A1917;margin-bottom:6px;">选择一个任务开始对话</p>'
        '<p style="font-size:13px;color:#A8A29E;">从左侧任务列表点击「开始」</p></div>',
        unsafe_allow_html=True)
    st.stop()

# ── Chat area ────────────────────────────────────────────────────────────────
pri=sel_task.get("priority","medium")
pc=_PC.get(pri,"#78716C")

# Compact task header
st.markdown(
    f'<div style="background:#FFFFFF;border:1px solid #E5E3DE;border-left:4px solid {pc};'
    f'padding:12px 18px;margin-bottom:16px;animation:fadeIn 0.3s;">'
    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
    f'<span style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{pc};">{pri}</span>'
    f'<span style="font-size:10px;color:#A8A29E;font-family:JetBrains Mono,monospace;">{sel_task.get("task_id","")}</span></div>'
    f'<div style="font-size:15px;font-weight:600;color:#1A1917;line-height:1.3;">{sel_task.get("task","")}</div>'
    +(f'<div style="font-size:12px;color:#A8A29E;margin-top:4px;font-style:italic;">{sel_task.get("priority_reason","")}</div>' if sel_task.get("priority_reason") else "")
    +f'</div>',
    unsafe_allow_html=True)

# Mode toggle（云端保留 UI，触发本地功能时在对话中提示）
mode = st.radio("", ["💬 问答模式", "🤖 Agent 模式"], horizontal=True, key="work_mode", label_visibility="collapsed")
st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

# Message history
msgs=st.session_state["work_messages"]
for idx,msg in enumerate(msgs):
    is_user=msg["role"]=="user"
    with st.chat_message("user" if is_user else "assistant"):
        st.markdown(msg["content"])

if mode == "💬 问答模式":
    if msgs:
        if st.button("🌐 搜索此任务相关资料",key="browser_btn",help="用 Selenium 打开浏览器搜索"):
            if not CAN_RUN_LOCAL_FEATURES:
                msgs.append({"role": "assistant", "content": local_deploy_hint("浏览器搜索")})
                st.rerun()
            kw=sel_task.get("task","工作")
            def run_browser(q):
                try:
                    from selenium import webdriver
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.common.keys import Keys
                    from webdriver_manager.chrome import ChromeDriverManager
                    from selenium.webdriver.chrome.service import Service
                    d=webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=webdriver.ChromeOptions())
                    d.get("https://www.google.com")
                    e=d.find_element(By.NAME,"q")
                    e.send_keys(f"{q} 解决方案"); e.send_keys(Keys.RETURN)
                    return f"✅ 已打开浏览器并搜索：{q} 解决方案"
                except Exception as ex: return f"❌ 浏览器演示失败：{ex}"
            with st.spinner("打开浏览器..."):
                r=run_browser(kw)
            msgs.append({"role":"assistant","content":r}); st.rerun()
    user_input=st.chat_input("针对此任务提问或请求协助...")
    if user_input:
        msgs.append({"role":"user","content":user_input})
        skill_txt=st.session_state.get("work_skill","")
        sys_p=(
            f"你是工作助手，用户：{cur_user}。"
            f"\n当前任务：{sel_task.get('task','')}。截止：{sel_task.get('deadline','未定')}。优先级：{sel_task.get('priority','')}。"
            +(f"\n\n技能背景：{skill_txt}" if skill_txt else "")
            +"\n\n请简洁、专业地回答，支持 Markdown 格式。"
        )
        api_key = cur_m["api_key"] or get_config_value("OPENAI_API_KEY", "")
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_BASE_URL"] = cur_m["base_url"] or get_config_value("OPENAI_BASE_URL", "https://api.deepseek.com")
        os.environ["OPENAI_MODEL"] = cur_m["model"] or get_config_value("OPENAI_MODEL", "deepseek-chat")
        if not api_key.strip():
            msgs.append({"role": "assistant", "content": "请在侧边栏配置 API Key，或在 Streamlit Secrets 中设置 OPENAI_API_KEY。"})
            st.rerun()
        from app.prototype.llm import call_llm
        hist="\n".join(f"{m['role'].upper()}: {m['content']}" for m in msgs[:-1])
        prompt=(hist+"\n" if hist else "")+f"USER: {user_input}"
        with st.spinner("思考中..."):
            reply=call_llm(prompt,system=sys_p) or "（模型无响应，请检查 API Key）"
        msgs.append({"role":"assistant","content":reply}); st.rerun()

else:  # 🤖 Agent 模式
    import subprocess
    # Agent 目标配置
    agent_target = st.session_state.get("agent_target", "")
    with st.expander("⚙ Agent 目标配置", expanded=not bool(agent_target)):
        st.markdown('<p style="font-size:12px;color:#78716C;margin-bottom:8px;">选择一种方式指定 OpenClaw 会话目标：</p>', unsafe_allow_html=True)
        target_mode = st.radio("", ["--to 手机号", "--agent 名称", "--session-id"], horizontal=True, key="agent_target_mode", label_visibility="collapsed")
        if target_mode == "--to 手机号":
            t = st.text_input("手机号（E.164格式，如 +8613800138000）", value=agent_target if agent_target.startswith("+") else "", key="agent_to_input")
            if t: st.session_state["agent_target"] = t; st.session_state["agent_target_flag"] = "--to"
        elif target_mode == "--agent 名称":
            t = st.text_input("Agent 名称（运行 openclaw agents list 查看）", value=agent_target if not agent_target.startswith("+") else "", key="agent_name_input")
            if t: st.session_state["agent_target"] = t; st.session_state["agent_target_flag"] = "--agent"
        else:
            t = st.text_input("Session ID", value=agent_target, key="agent_sid_input")
            if t: st.session_state["agent_target"] = t; st.session_state["agent_target_flag"] = "--session-id"
    agent_target = st.session_state.get("agent_target", "")
    agent_flag   = st.session_state.get("agent_target_flag", "--to")
    def check_gateway():
        try:
            r=subprocess.run(["openclaw","health"],capture_output=True,text=True,timeout=5)
            out=(r.stdout+r.stderr).strip()
            return True,out
        except subprocess.TimeoutExpired: return False,"Gateway 未响应（超时）"
        except Exception as e: return False,str(e)
    gw_ok,gw_msg=check_gateway()
    if gw_ok:
        st.markdown('<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#DCFCE7;border:1px solid #BBF7D0;border-radius:3px;margin-bottom:12px;font-size:13px;color:#16A34A;">🟢 Gateway 运行中</div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="padding:10px 14px;background:#FEF3C7;border:1px solid #FDE68A;border-radius:3px;margin-bottom:12px;font-size:13px;color:#D97706;">🟡 Gateway 未运行<br><span style="font-size:11px;color:#92400E;">{gw_msg[:120]}</span></div>',unsafe_allow_html=True)
        if st.button("▶ 启动 Gateway",key="start_gw"):
            if not CAN_RUN_LOCAL_FEATURES:
                msgs.append({"role": "assistant", "content": local_deploy_hint("启动 OpenClaw Gateway")})
                st.rerun()
            subprocess.Popen(["openclaw","gateway","--force"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            st.info("Gateway 启动中，请稍候几秒后刷新页面...")
    if not agent_target:
        st.warning("请先在上方配置 Agent 目标（手机号 / Agent名称 / Session ID）")
    else:
        st.markdown(f'<div style="font-size:12px;color:#78716C;margin-bottom:10px;">目标：<code>{agent_flag} {agent_target}</code> · OpenClaw Agent 将在你的电脑上自主执行</div>',unsafe_allow_html=True)
        agent_input=st.chat_input("向 OpenClaw Agent 发送指令...")
        if agent_input:
            msgs.append({"role":"user","content":f"🤖 [Agent] {agent_input}"})
            if not CAN_RUN_LOCAL_FEATURES:
                msgs.append({"role": "assistant", "content": local_deploy_hint("OpenClaw Agent")})
                st.rerun()
            task_ctx=f"当前任务：{sel_task.get('task','')}。截止：{sel_task.get('deadline','未定')}。"
            full_msg=f"{task_ctx} 用户指令：{agent_input}"
            with st.spinner("OpenClaw Agent 执行中..."):
                try:
                    result=subprocess.run(
                        ["openclaw","agent",agent_flag,agent_target,"--message",full_msg],
                        capture_output=True,text=True,timeout=60
                    )
                    out=(result.stdout+result.stderr).strip()
                    reply=out if out else "（Agent 无输出，请检查 Gateway 状态）"
                except subprocess.TimeoutExpired: reply="⏱ Agent 执行超时（60s），任务可能仍在后台运行。"
                except Exception as e: reply=f"❌ 调用失败：{e}"
            msgs.append({"role":"assistant","content":reply}); st.rerun()

