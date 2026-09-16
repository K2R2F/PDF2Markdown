"""Persistence UI boundary: disk errors never masquerade as saved results."""
from dataclasses import asdict
import sqlite3
import streamlit as st
from core.models import Settings
from storage import state
from storage.paths import data_directory

STORAGE_ERRORS = (OSError, sqlite3.Error, ValueError, TypeError, KeyError)


def initialize_preferences():
    if st.session_state.get('preferences_loaded'):
        return
    try:
        settings, directory = state.load_preferences()
    except STORAGE_ERRORS as exc:
        settings, directory = Settings(), str(data_directory() / 'output')
        st.session_state.persistence_warning = f'設定を読み込めませんでした。初期値で起動しました: {exc}'
        st.session_state.preferences_read_failed = True
    for key, value in asdict(settings).items():
        st.session_state.setdefault('setting_' + key, value)
    st.session_state.setdefault('save_directory', directory)
    st.session_state.preferences_loaded = True


def persist_preferences(settings):
    if warning := st.session_state.get('persistence_warning'):
        st.warning(warning)
    if st.session_state.get('preferences_read_failed'):
        if st.button('現在の設定を保存して復旧を試す', key='repair_preferences'):
            st.session_state.preferences_read_failed = False
        else:
            return
    current = (settings, st.session_state.save_directory)
    if current == st.session_state.get('persisted_preferences'):
        return
    try:
        state.save_preferences(*current)
        st.session_state.persisted_preferences = current
        st.session_state.pop('persistence_warning', None)
    except STORAGE_ERRORS as exc:
        st.error(f'設定を保存できませんでした。再起動すると変更が失われる可能性があります: {exc}')


def checkpoint(status):
    try:
        state.save_batch(st.session_state.batch_id, st.session_state.result_settings,
                         st.session_state.results, status)
    except STORAGE_ERRORS as exc:
        st.error(f'履歴を保存できませんでした。結果をMarkdownまたはZIPで保存してください: {exc}')


def render_history():
    with st.expander('保存された変換履歴・復元'):
        st.caption('結果の本文をこのPCに保存します。元PDFと入力URLは保存しません。最新20件を表示します。')
        st.caption(f'設定・履歴の保存先: {data_directory()}')
        try:
            rows = state.list_batches()
            if not rows:
                st.info('保存された履歴はありません。')
                return
            labels = {'running': '完了未確認', 'complete': '処理終了', 'failure': '失敗あり'}
            selected = st.selectbox('復元する履歴', rows,
                format_func=lambda r: f'{r[1][:19]} UTC / {labels[r[2]]} / {r[0][:8]}', key='history_choice')
            if st.button('選択した結果を復元', key='restore_history'):
                settings, results, status = state.load_batch(selected[0])
                st.session_state.results = results
                st.session_state.result_settings = settings
                st.session_state.pop('zip_bytes', None)
                st.session_state.pop('saved_files', None)
                st.session_state.history_notice = ('完了を確認できない履歴です。保存できた結果だけ復元しました。'
                    if status == 'running' else '保存された結果を復元しました。再変換はしていません。')
                st.rerun()
            if st.button('選択した履歴を削除', key='delete_history'):
                state.delete_batch(selected[0])
                st.rerun()
            st.caption('履歴の削除は、別途保存したMarkdown・ZIPや元PDFには影響しません。')
        except STORAGE_ERRORS as exc:
            st.error(f'履歴を読み書きできませんでした: {exc}')
