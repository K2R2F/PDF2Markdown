"""Environment support panel; independent reruns keep conversion results intact."""
import sys
from pathlib import Path

import streamlit as st

from environment_support import LABELS, inspect_environment, job_snapshot, start_setup


@st.cache_data(ttl=60, show_spinner=False)
def environment_report():
    return inspect_environment()


@st.fragment(run_every='2s')
def render_environment_panel():
    job = job_snapshot()
    running = job.get('state') == 'running'
    if job and not running and st.session_state.get('last_setup_log') != job['log']:
        environment_report.clear()
        st.session_state.last_setup_log = job['log']
        st.rerun()
    report = environment_report()
    missing_count = sum(not entry['ready'] for entry in report.values())
    title = f'環境チェック・インストール支援　·　要設定 {missing_count}件'
    with st.expander(title, expanded=bool(job)):
        st.caption(f'使用中のPython: {Path(sys.executable).as_posix()}')
        st.caption('導入済みのPythonパッケージはバージョンを表示します。「実行確認・設定」で別プロセスから読み込みを確認できます。OCRモデルは初回変換時に自動取得します。')
        for component, label in LABELS.items():
            item = report[component]
            description, action = st.columns([3, 1])
            with description:
                st.markdown(f'**{label}** · ' + ('導入済み' if item['ready'] else '未導入・要設定'))
                st.caption(item['detail'] or 'パッケージが見つかりません')
                if item['missing']:
                    st.caption('不足: ' + ', '.join(item['missing']))
                for note in item['notes']:
                    st.caption(note)
            with action:
                button = '実行確認・設定' if item['ready'] else 'インストール・設定'
                if st.button(button, key=f'install_{component}', disabled=running, use_container_width=True):
                    try:
                        start_setup(component)
                        st.rerun()
                    except (OSError, RuntimeError, ValueError) as exc:
                        st.error(str(exc))
        st.caption('Pythonパッケージはこのアプリの仮想環境へ導入します。TesseractはUB Mannheim配布版を照合後に導入し、英語・日本語・簡体字・向き検出データを設定します。Windowsの確認が出る場合は操作してください。ネット接続と数分以上の時間が必要です。')
        if st.button('不足分をまとめてインストール・設定', key='install_all', disabled=running):
            try:
                start_setup('all')
                st.rerun()
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(str(exc))
        if st.button('状態を再チェック', key='check_environment', disabled=running):
            environment_report.clear()
            st.rerun()
        if job:
            if running:
                st.info('設定を実行中です。ログを自動更新します。アプリ本体は終了せずにお待ちください。')
            elif job['state'] == 'success':
                completed = LABELS.get(job['component'], '選択した全項目')
                st.success(f'{completed}の設定・実行確認が完了しました。')
                if job['component'] in ('tesseract', 'all') and report['tesseract']['ready']:
                    st.caption('Tesseractの設定は次の変換から自動適用します。')
                st.caption('Pythonパッケージを新規導入した場合、読み込み済みライブラリーへの反映にはアプリの再起動が必要になることがあります。変換結果を保存してから再起動してください。')
            else:
                st.error('完了できなかった項目があります。ログを確認し、通信・権限の問題を解消後に再実行してください。')
            st.code(job.get('output', '') or '処理を開始しています…', language='text')
            st.caption(f'ログ保存先: {Path(job["log"]).as_posix()}')
