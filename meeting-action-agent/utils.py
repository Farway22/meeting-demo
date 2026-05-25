"""Shared CSS, helpers, and render functions for MeetingMind demo."""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any

_B = Path(__file__).resolve().parent / "backend"
if str(_B) not in sys.path:
    sys.path.insert(0, str(_B))

import streamlit as st

from cloud_config import get_config_value as get_secret  # noqa: F401
from cloud_config import is_cloud_runtime, local_only_features_enabled


# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[data-testid="stAppViewContainer"]{background:#F7F6F3!important;font-family:'Outfit',sans-serif;}
[data-testid="stSidebar"]{background:#1A1917!important;}
[data-testid="stSidebar"] *{color:#E7E5E4!important;}
[data-testid="stSidebar"] .stTextInput input,[data-testid="stSidebar"] .stSelectbox select,[data-testid="stSidebar"] .stTextArea textarea{
  background:#292524!important;border:1px solid #44403C!important;color:#E7E5E4!important;
  font-family:'JetBrains Mono',monospace;font-size:12px;border-radius:3px;}
[data-testid="stSidebar"] label{color:#A8A29E!important;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;}
.main .block-container{padding:2.5rem 3rem 4rem 3rem;max-width:1400px;}
textarea{font-family:'Outfit',sans-serif!important;font-size:14px!important;background:#FFFFFF!important;
  border:1px solid #E5E3DE!important;border-radius:3px!important;color:#1A1917!important;}
textarea:focus{border-color:#1A1917!important;box-shadow:none!important;}
.stButton>button{background:#1A1917!important;color:#F7F6F3!important;border:none!important;
  border-radius:3px!important;font-family:'Outfit',sans-serif!important;font-weight:600!important;
  font-size:14px!important;letter-spacing:0.05em!important;height:46px!important;}
.stButton>button:hover{background:#292524!important;}
.stButton>button[kind="secondary"]{background:transparent!important;color:#78716C!important;border:1px solid #E5E3DE!important;}
.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #E5E3DE!important;gap:0!important;}
.stTabs [data-baseweb="tab"]{font-family:'Outfit',sans-serif!important;font-size:13px!important;font-weight:500!important;
  color:#78716C!important;padding:10px 22px!important;border:none!important;background:transparent!important;}
.stTabs [aria-selected="true"]{color:#1A1917!important;border-bottom:2px solid #1A1917!important;}
footer{visibility:hidden;}
/* 确保收起后的侧边栏展开箭头始终可见可点击 */
[data-testid="collapsedControl"]{visibility:visible!important;opacity:1!important;display:flex!important;}
</style>"""

_PC = {"high":"#DC2626","medium":"#D97706","low":"#16A34A"}
_PB = {"high":"#FEE2E2","medium":"#FEF3C7","low":"#DCFCE7"}

def apply_css():
    st.markdown(CSS, unsafe_allow_html=True)

def bdg(txt, bg="#F1F0EE", col="#57534E"):
    return (f'<span style="display:inline-block;font-size:10px;font-weight:600;letter-spacing:0.08em;'
            f'text-transform:uppercase;padding:3px 8px;border-radius:2px;background:{bg};color:{col};'
            f'font-family:Outfit,sans-serif;">{txt}</span>')

def conf_bar(c):
    pct = int(c * 100)
    col = _PC["low"] if c >= 0.7 else (_PC["medium"] if c >= 0.4 else _PC["high"])
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;">'
            f'<span style="width:48px;height:3px;background:#E5E3DE;border-radius:2px;display:inline-block;overflow:hidden;">'
            f'<span style="width:{pct}%;height:100%;background:{col};display:block;"></span></span>'
            f'<span style="font-size:11px;color:#A8A29E;font-family:JetBrains Mono,monospace;">{c:.2f}</span></span>')

def owner_chips(owners, resolution):
    if not owners:
        return '<span style="font-size:12px;color:#A8A29E;">未分配</span>'
    chips = []
    for o in owners:
        nm = o.get("name", ""); rl = o.get("role", "")
        lbl = nm + (f" · {rl}" if rl and rl != nm else "")
        is_r = (resolution == "role")
        bg = "#EDE9FE" if is_r else "#FAFAF9"
        c  = "#7C3AED" if is_r else "#44403C"
        b  = "#DDD6FE" if is_r else "#E5E3DE"
        chips.append(f'<span style="font-size:11px;font-weight:500;padding:3px 10px;border:1px solid {b};'
                     f'border-radius:2px;color:{c};background:{bg};font-family:Outfit,sans-serif;">{lbl}</span>')
    return '<div style="display:flex;gap:6px;flex-wrap:wrap;">' + ''.join(chips) + '</div>'

def parse_participants(raw: str) -> list[dict]:
    out = []
    for ln in raw.strip().splitlines():
        ln = ln.strip()
        if not ln: continue
        if "/" in ln:
            n, r = ln.split("/", 1)
            out.append({"name": n.strip(), "role": r.strip()})
        else:
            out.append({"name": ln, "role": ""})
    return out

# ── Execution Plan ────────────────────────────────────────────────────────────
def render_plan(plan: list[dict[str, Any]]) -> None:
    if not plan: st.info("无执行计划"); return
    mains = [s for s in plan if s.get("track") == "main"]
    pars  = [s for s in plan if s.get("track") != "main"]
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:12px;">'
        f'<span style="font-size:15px;font-weight:700;color:#1A1917;font-family:Outfit,sans-serif;">主流程</span>'
        f'<span style="font-size:12px;color:#78716C;">Main Flow</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:#A8A29E;margin-left:auto;">{len(mains)} 步</span></div>',
        unsafe_allow_html=True)
    for s in mains: _plan_row(s, True)
    if pars:
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:12px;margin:28px 0 12px;padding-top:20px;border-top:1px dashed #E5E3DE;">'
            f'<span style="font-size:15px;font-weight:700;color:#78716C;font-family:Outfit,sans-serif;">并行任务</span>'
            f'<span style="font-size:12px;color:#A8A29E;">Parallel · 可与主流程同步推进</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:#A8A29E;margin-left:auto;">{len(pars)} 项</span></div>',
            unsafe_allow_html=True)
        for s in pars: _plan_row(s, False)

def _plan_row(s: dict, is_main: bool) -> None:
    is_blk = s.get("is_blocker", False)
    lc = "#DC2626" if is_blk else ("#1A1917" if is_main else "#D6D3D1")
    lw = "4px" if is_blk else "3px"
    bg = "#FFFBFB" if is_blk else ("#FFFFFF" if is_main else "#FAFAF9")
    tc = "#1A1917" if is_main else "#78716C"
    fw = "600" if is_main else "400"
    blk_h = ('<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;'
              'letter-spacing:0.06em;text-transform:uppercase;padding:3px 8px;border-radius:2px;'
              'background:#DC2626;color:#FFFFFF;font-family:Outfit,sans-serif;">⚠ BLOCKER</span> ') if is_blk else ""
    pri = s.get("priority", "medium")
    pb  = bdg(pri, _PB.get(pri, "#F1F0EE"), _PC.get(pri, "#57534E"))
    step_txt = f'{s["step"]:02d}' if is_main else "—"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:{bg};'
        f'border:1px solid {"#FECACA" if is_blk else "#E5E3DE"};border-left:{lw} solid {lc};margin-bottom:5px;">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:#A8A29E;min-width:26px;">{step_txt}</span>'
        f'<span style="flex:1;font-size:15px;font-weight:{fw};color:{tc};font-family:Outfit,sans-serif;">{s["task"]}</span>'
        f'<span style="display:flex;gap:6px;align-items:center;">{blk_h}{pb}</span></div>',
        unsafe_allow_html=True)

# ── Tasks ─────────────────────────────────────────────────────────────────────
def render_tasks(tasks: list[dict[str, Any]]) -> None:
    if not tasks: st.info("无任务"); return
    for pri in ("high", "medium", "low"):
        grp = [t for t in tasks if t.get("priority") == pri]
        if not grp: continue
        st.markdown(f'<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
                    f'color:{_PC[pri]};margin:20px 0 8px;">{pri.upper()} · {len(grp)}个任务</p>', unsafe_allow_html=True)
        for t in grp: _task_card(t, pri)

def _task_card(t: dict, pri: str) -> None:
    pc  = _PC[pri]
    owners_h = owner_chips(t.get("owners") or [], t.get("owner_resolution", ""))
    ddl  = t.get("deadline") or "—"
    conf = t.get("confidence", 0.5)
    tl   = t.get("task_level", "atomic")
    blk  = t.get("is_blocker", False)
    deps = t.get("dependencies") or []
    ev   = t.get("evidence", "")
    lb = "#EDE9FE" if tl == "composite" else "#F1F0EE"
    lc = "#7C3AED" if tl == "composite" else "#78716C"
    dep_h = ""
    if deps:
        dtags = "".join(f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;padding:2px 6px;'
                        f'background:#F1F0EE;color:#78716C;border-radius:2px;margin-right:4px;">{d}</span>' for d in deps)
        dep_h = f'<div style="margin-top:8px;font-size:11px;color:#A8A29E;">前置依赖 {dtags}</div>'
    subs = t.get("subtasks") or []; sub_h = ""
    if subs:
        rows = "".join(f'<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #F1F0EE;">'
                       f'<span style="font-size:11px;color:#A8A29E;min-width:14px;">·</span>'
                       f'<span style="font-size:13px;color:#44403C;flex:1;">{s.get("task","")}</span>'
                       f'<span style="font-size:11px;color:#A8A29E;">{s.get("owner") or ""}</span></div>' for s in subs)
        sub_h = (f'<div style="margin-top:12px;padding:10px 14px;background:#FAFAF9;border:1px solid #F1F0EE;">'
                 f'<p style="font-size:10px;font-weight:600;letter-spacing:0.08em;color:#A8A29E;'
                 f'text-transform:uppercase;margin:0 0 6px 0;">SUBTASKS</p>{rows}</div>')
    rr = t.get("priority_reason", "")
    rr_h = (
        f'<div style="margin:10px 0 8px;padding:8px 12px;background:#F7F6F3;border-left:3px solid {pc};">'
        f'<span style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#A8A29E;">优先级原因</span>'
        f'<div style="font-size:13px;color:#44403C;margin-top:3px;line-height:1.5;">{rr}</div></div>'
    ) if rr else ""
    meta_h = (
        f'<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:10px;'
        f'padding-top:8px;border-top:1px solid #F1F0EE;">'
        f'<span style="font-size:11px;color:#C4BFB8;">📅 {ddl}</span>'
        f'<span style="font-size:11px;color:#C4BFB8;">置信度 {conf_bar(conf)}</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:9px;color:#D6D3D1;margin-left:auto;">{t.get("task_id","")}</span>'
        f'</div>'
    )
    ev_h = (
        f'<div style="margin-top:6px;font-size:11px;color:#C4BFB8;border-left:2px solid #F1F0EE;'
        f'padding-left:8px;font-style:italic;line-height:1.5;">{ev}</div>'
    ) if ev else ""
    top_border = "#DC2626" if blk else pc
    blk_badge = ('<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;'
                 'letter-spacing:0.06em;text-transform:uppercase;padding:3px 8px;border-radius:2px;'
                 'background:#DC2626;color:#FFFFFF;font-family:Outfit,sans-serif;">⚠ BLOCKER</span> ') if blk else ""
    st.markdown(
        f'<div style="background:#FFFFFF;border:1px solid {"#FECACA" if blk else "#E5E3DE"};'
        f'border-top:3px solid {top_border};padding:18px 20px 14px 20px;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">{blk_badge}{bdg(tl,lb,lc)}</div>'
        f'<div style="font-size:16px;font-weight:600;color:#1A1917;margin-bottom:8px;line-height:1.3;'
        f'font-family:Outfit,sans-serif;">{t.get("task","")}</div>'
        f'<div style="margin-bottom:6px;">{owners_h}</div>'
        f'{rr_h}{dep_h}{sub_h}{meta_h}{ev_h}</div>',
        unsafe_allow_html=True)

# ── Personal Todos ─────────────────────────────────────────────────────────────
def render_todos(todos: dict[str, list[dict]]) -> None:
    if not todos: st.info("无待办"); return
    people = list(todos.keys())
    if "未分配" in people: people = [p for p in people if p != "未分配"] + ["未分配"]
    cols = st.columns(min(len(people), 4))
    for i, person in enumerate(people):
        with cols[i % 4]:
            hc = "#A8A29E" if person == "未分配" else "#1A1917"
            st.markdown(
                f'<div style="border-bottom:2px solid {hc};padding-bottom:8px;margin-bottom:12px;">'
                f'<span style="font-size:14px;font-weight:600;color:{hc};font-family:Outfit,sans-serif;">{person}</span>'
                f'<span style="font-size:11px;color:#A8A29E;margin-left:8px;">{len(todos[person])}项</span></div>',
                unsafe_allow_html=True)
            for item in todos[person]:
                pri2 = item.get("priority", "medium")
                pc2  = _PC.get(pri2, "#78716C")
                ddl2 = item.get("deadline") or ""
                st.markdown(
                    f'<div style="border-left:2px solid {pc2};padding:8px 10px;margin-bottom:7px;'
                    f'background:#FFFFFF;border-top:1px solid #F1F0EE;border-right:1px solid #F1F0EE;border-bottom:1px solid #F1F0EE;">'
                    f'<div style="font-size:13px;font-weight:500;color:#1A1917;line-height:1.4;'
                    f'font-family:Outfit,sans-serif;margin-bottom:4px;">{item.get("task","")}</div>'
                    f'<div style="display:flex;justify-content:space-between;">'
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:9px;color:#A8A29E;">{item.get("task_id","")}</span>'
                    f'<span style="font-size:11px;color:#A8A29E;">{ddl2}</span></div></div>',
                    unsafe_allow_html=True)

# ── Download helpers ──────────────────────────────────────────────────────────
def todos_to_json(todos: dict) -> str:
    import json
    return json.dumps(todos, ensure_ascii=False, indent=2)

def todos_to_md(todos: dict, tasks: list[dict] | None = None) -> str:
    lines = ["# 会议任务清单\n"]
    for person, items in todos.items():
        lines.append(f"\n## {person}\n")
        for item in items:
            ddl = f" (截止: {item['deadline']})" if item.get("deadline") else ""
            blk = " 🔴" if any(t.get("task_id") == item.get("task_id") and t.get("is_blocker")
                               for t in (tasks or [])) else ""
            lines.append(f"- [{item['priority'].upper()}]{blk} {item['task']}{ddl}")
    return "\n".join(lines)
 