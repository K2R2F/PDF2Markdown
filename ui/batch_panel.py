"""Nonblocking PDF conversion controls."""
import sqlite3
import streamlit as st
from environment.jobs import job_snapshot
from execution import controller


def render_batch(settings, mode, uploads, archive, url_text):
    ready = bool(uploads or archive or url_text.strip())
    setup, conversion = job_snapshot(), controller.snapshot()
    busy = any(j.get('state') == 'running' or j.get('blocked') for j in (setup, conversion))
    minutes = st.number_input('処理全体の時間上限（分）', min_value=1, max_value=120, value=30,
        help='URL取得・モデル準備・全PDFの変換を含みます。超過時は停止し、完了済みの結果を残します。')
    if st.button('Markdownに変換', type='primary', disabled=not ready or busy, use_container_width=True):
        try:
            files = [(f.name, f.getvalue()) for f in uploads] if mode == 'ファイル' else []
            if mode == 'ZIP' and archive:
                files = [(archive.name, archive.getvalue())]
            urls = [u.strip() for u in url_text.splitlines() if u.strip()] if mode == 'URL' else []
            batch_id = controller.start(settings, mode, files, urls, int(minutes) * 60)
            st.session_state.active_conversion = batch_id
            st.session_state.results = []
            st.session_state.result_settings = settings
            st.session_state.pop('zip_bytes', None)
            st.session_state.pop('saved_files', None)
        except Exception as exc:
            st.error(f'変換を開始できませんでした: {exc}')


@st.fragment(run_every='1s')
def render_activity():
    job = controller.snapshot()
    if not job:
        return
    if job.get('state') == 'running':
        st.info(job.get('label', '変換中'))
        if st.button('変換をキャンセル', key='cancel_conversion'):
            controller.cancel(job['id'])
            st.warning('停止を要求しました。プロセスツリーの終了を確認しています。')
    elif job.get('blocked'):
        st.error(job.get('error') or '停止確認が取れないため追加処理を停止しています。')
    elif st.session_state.get('active_conversion') == job['id']:
        from storage import state
        try:
            settings, results, _ = state.load_batch(job['id'])
            st.session_state.results = results
            st.session_state.result_settings = settings
            st.session_state.pop('zip_bytes', None)
            st.session_state.pop('saved_files', None)
            st.session_state.pop('active_conversion', None)
            st.session_state.conversion_notice = job.get('error', '')
            st.rerun()
        except (OSError, ValueError, sqlite3.Error) as exc:
            st.error(f'結果を読み込めませんでした: {exc}')
