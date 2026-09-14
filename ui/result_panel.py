from __future__ import annotations

import streamlit as st
from core.markdown_export import make_zip, output_names
from saving import save_file

def save_to_folder(key: str, filename: str, data: str | bytes) -> None:
    try:
        path = save_file(st.session_state.save_directory, filename, data)
        st.session_state.setdefault('saved_files', {})[key] = str(path)
        st.toast(f'保存しました: {path.name}', icon='✅')
    except (OSError, ValueError) as exc:
        st.error(f'保存できませんでした。保存先と書き込み権限を確認してください: {exc}')



def render_results():
    results = st.session_state.get('results', [])
    st.divider()
    st.subheader('02　変換結果')
    if not results:
        st.info('ここに変換結果が表示されます。PDFを追加して変換を開始してください。')
    else:
        saved_settings = st.session_state.result_settings
        st.caption(f'結果の設定: {saved_settings.engine} / {saved_settings.language} / OCR {saved_settings.ocr_mode}。設定変更は次の変換に適用されます。')
        a, b, c = st.columns(3)
        a.metric('完了', sum(r.status == 'success' for r in results))
        b.metric('一部変換', sum(r.status == 'partial_success' for r in results))
        c.metric('失敗', sum(r.status == 'failure' for r in results))
        if 'zip_bytes' not in st.session_state:
            st.session_state.zip_bytes = make_zip(results, saved_settings)
        st.caption(f'保存先: {st.session_state.save_directory}')
        if st.button('すべてZIPで保存（処理レポート付き）', use_container_width=True, key='save_zip'):
            save_to_folder('zip', 'markdown-results.zip', st.session_state.zip_bytes)
        if saved_path := st.session_state.get('saved_files', {}).get('zip'):
            st.success(f'保存済み: {saved_path}')
        names = output_names(results)
        for index, result in enumerate(results):
            label = {'success': '完了', 'partial_success': '一部変換', 'failure': '失敗'}[result.status]
            detail, action = st.columns([3, 1])
            with action:
                if result.status != 'failure':
                    if st.button('Markdownを保存', key=f'save_{index}', use_container_width=True):
                        save_to_folder(str(index), names[index], result.markdown)
            if saved_path := st.session_state.get('saved_files', {}).get(str(index)):
                st.success(f'保存済み: {saved_path}')
            with detail.expander(f'{label}　{result.name}　·　{result.pages}ページ / {result.seconds:.1f}秒'):
                if result.error:
                    st.warning(result.error)
                if result.status != 'failure':
                    # Code preview avoids executing HTML or fetching remote images from untrusted PDFs.
                    st.code(result.markdown[:100_000], language='markdown', wrap_lines=True)
                    if len(result.markdown) > 100_000:
                        st.caption('プレビューは先頭100,000文字です。ダウンロードには全文を含みます。')
        if st.button('結果をクリア'):
            for key in ('results', 'zip_bytes', 'result_settings', 'saved_files'):
                st.session_state.pop(key, None)
            st.rerun()
