from __future__ import annotations

import streamlit as st
from pathlib import Path

def configure_page():
    st.set_page_config(page_title='PDF → Markdown | Docling', page_icon='📄', layout='wide')
    st.html((Path(__file__).resolve().parents[1] / 'ui_ja.html').read_text(encoding='utf-8'), unsafe_allow_javascript=True)
    st.markdown('''<style>
    .block-container {max-width:1180px;padding-top:2.4rem}
    h1 {letter-spacing:-.045em;font-weight:750!important}
    [data-testid="stMetric"] {background:white;border:1px solid #dce6e1;border-radius:14px;padding:16px}
    [data-testid="stFileUploader"] {border-radius:16px}
    .eyebrow {color:#13796b;font-size:12px;letter-spacing:.2em;font-weight:700}
    .intro {color:#65776f;font-size:17px;margin-bottom:26px}
    </style>''', unsafe_allow_html=True)


def render_header():
    st.markdown('<div class="eyebrow">文書変換ワークスペース · Docling使用</div>', unsafe_allow_html=True)
    st.title('PDFから、使えるMarkdownへ。')
    st.markdown('<div class="intro">複数の資料をまとめて変換。見出し、本文、表を、次の作業につながる形に。</div>', unsafe_allow_html=True)
