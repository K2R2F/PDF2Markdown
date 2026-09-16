from __future__ import annotations

import streamlit as st
from core.models import Settings
from ui.persistence import persist_preferences

def render_settings() -> Settings:
    with st.sidebar:
        st.markdown('### 変換設定')
        st.caption('ドキュメントに合わせて調整')
        engine = st.selectbox('OCRエンジン', ['easyocr', 'rapidocr', 'tesseract'], key='setting_engine',
                              format_func=lambda x: {'easyocr': 'EasyOCR · 日本語＋英語に推奨',
                                                     'rapidocr': 'RapidOCR · ONNX Runtime',
                                                     'tesseract': 'Tesseract · 別途インストール'}[x])
        language = st.selectbox('文書の言語', ['ja_en', 'en', 'zh_en'], key='setting_language',
                                format_func=lambda x: {'ja_en': '日本語＋英語', 'en': '英語', 'zh_en': '中国語（簡体字）＋英語'}[x])
        if engine == 'rapidocr':
            st.caption('RapidOCRは主言語の認識モデルを1つ選びます。日英混在の精度はEasyOCRと比較してください。')
        if engine == 'tesseract':
            st.info('画面下部の「環境チェック・インストール支援」で本体と言語データを自動設定できます。')
        ocr_mode = st.radio('OCRの実行方法', ['auto', 'force', 'off'], key='setting_ocr_mode',
                            format_func=lambda x: {'auto': '必要な領域にOCR（標準）', 'force': '全ページにOCR', 'off': 'OCRなし（テキストPDF）'}[x])
        tables = st.toggle('表の構造を復元', key='setting_tables')
        images = st.toggle('画像をMarkdownに埋め込む', key='setting_images',
                           help='Base64で画像を埋め込みます。ファイルサイズが増えます。ビューアによっては画像表示に非対応です。')
        max_pages = st.number_input('1ファイルのページ上限', min_value=1, max_value=1000, key='setting_max_pages',
                                    help='超過したPDFは失敗として報告します。途中で切り捨てません。')
        st.divider()
        st.markdown('### 保存先')
        st.text_input('保存先フォルダー', key='save_directory')
        st.caption('保存ボタンでこのPCのフォルダーへ直接保存します。同名ファイルには連番を付けます。')
        st.divider()
        st.caption('ローカル処理 / Docling\n\n初回変換時はモデルのダウンロードに数分かかることがあります。PDF本文を外部AI APIへ送信しません。')

    settings = Settings(engine, language, ocr_mode, tables, images, int(max_pages))
    persist_preferences(settings)
    return settings
