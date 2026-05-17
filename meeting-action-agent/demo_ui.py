"""MeetingMind · 首页"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from cloud_config import is_cloud_runtime
from utils import apply_css

st.set_page_config(page_title="MeetingMind", page_icon="◆", layout="wide", initial_sidebar_state="collapsed")
apply_css()

if is_cloud_runtime():
    st.caption("☁️ 云端演示版 · 请在 App Settings → Secrets 配置 OPENAI_API_KEY")

# 额外首页样式
st.markdown("""
<style>
.home-card {
    background:#FFFFFF;border:1px solid #E5E3DE;padding:40px 36px;
    cursor:pointer;transition:border-color 0.15s,box-shadow 0.15s;
    height:100%;
}
.home-card:hover{border-color:#1A1917;box-shadow:0 2px 12px rgba(0,0,0,0.06);}
.home-icon{font-size:32px;margin-bottom:16px;}
.home-title{font-family:'Outfit',sans-serif;font-size:20px;font-weight:700;color:#1A1917;margin-bottom:8px;letter-spacing:-0.3px;}
.home-desc{font-size:14px;color:#78716C;line-height:1.6;}
.home-tag{display:inline-block;font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
    padding:3px 8px;border-radius:2px;margin-top:16px;}
</style>""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:60px 0 48px;">'
    '<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:40px;color:#1A1917;letter-spacing:-1px;margin-bottom:12px;">'
    'Meeting<span style="color:#DC2626;">Mind</span></div>'
    '<div style="font-size:16px;color:#78716C;margin-bottom:6px;">会议纪要 · 结构化行动 · 智能协作</div>'
    '<div style="height:1px;background:#E5E3DE;width:60px;margin:24px auto 0;"></div>'
    '</div>',
    unsafe_allow_html=True)

# ── Two cards ─────────────────────────────────────────────────────────────────
_, col1, gap, col2, _ = st.columns([1, 3, 0.3, 3, 1])

with col1:
    st.markdown("""
<div class="home-card">
  <div class="home-icon">📋</div>
  <div class="home-title">总结会议</div>
  <div class="home-desc">粘贴会议纪要，AI 自动提取任务、负责人、截止日期，生成执行计划与个人待办。</div>
  <span class="home-tag" style="background:#FEE2E2;color:#DC2626;">Meeting Analysis</span>
</div>""", unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    if st.button("进入 →", key="go_meeting", use_container_width=True):
        st.switch_page("pages/1_会议分析.py")

with col2:
    st.markdown("""
<div class="home-card">
  <div class="home-icon">💼</div>
  <div class="home-title">开始工作</div>
  <div class="home-desc">上传任务清单，AI 助手结合任务上下文与你对话协作，支持多模型切换与技能模板。</div>
  <span class="home-tag" style="background:#DCFCE7;color:#16A34A;">Work Mode</span>
</div>""", unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    if st.button("进入 →", key="go_work", use_container_width=True):
        st.switch_page("pages/2_工作模式.py")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;margin-top:64px;font-size:11px;color:#A8A29E;letter-spacing:0.06em;">'
    'v0.5 · prototype · MeetingMind</div>',
    unsafe_allow_html=True)
