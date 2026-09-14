from __future__ import annotations

import streamlit as st


def render_inputs():
    left, right = st.columns([2, 1])
    with left:
        st.subheader('01　PDFを追加')
    with right:
        st.caption('最大30件 · 1件100 MB · 合計300 MB')
    mode = st.segmented_control('入力方法', ['ファイル', 'URL', 'ZIP'], default='ファイル', selection_mode='single')
    uploads, archive, url_text = [], None, ''
    if mode == 'ファイル':
        uploads = st.file_uploader('PDFをドラッグ＆ドロップ、または選択', type=['pdf'], accept_multiple_files=True)
    elif mode == 'URL':
        url_text = st.text_area('PDFのURLを1行に1つ入力', height=150,
                                placeholder='https://example.com/report.pdf\nhttps://example.com/research.pdf')
        st.caption('公開PDFの直接URLに対応。拡張子なし・リダイレクトも可。ログインが必要な共有ページは、PDFをダウンロードして「ファイル」で追加してください。')
    elif mode == 'ZIP':
        archive = st.file_uploader('PDFをまとめたZIPを選択', type=['zip'])
        st.caption('サブフォルダー内のPDFも対象です。PDF以外は無視します。暗号化ZIPは非対応です。')


    return mode, uploads, archive, url_text
