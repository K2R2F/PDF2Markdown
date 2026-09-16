from __future__ import annotations

import streamlit as st
import time
from core.models import Result
from core.pdf_validation import MAX_FILES, MAX_TOTAL, check_batch, validate_pdf
from core.url_input import fetch_pdf
from core.zip_input import read_zip
from environment.jobs import job_snapshot
from ui.converter_cache import get_converter

def render_batch(settings, mode, uploads, archive, url_text):
    ready = bool(uploads or archive or url_text.strip())
    environment_job = job_snapshot()
    setup_busy = environment_job.get('state') == 'running' or environment_job.get('blocked', False)
    if setup_busy:
        st.info('環境設定を実行中です。完了後に変換できます。')
    if st.button('Markdownに変換', type='primary', disabled=not ready or setup_busy, use_container_width=True):
        # Persist each completed result immediately so a UI rerun does not erase it.
        st.session_state.results = []
        st.session_state.result_settings = settings
        st.session_state.pop('zip_bytes', None)
        st.session_state.pop('saved_files', None)
        items = []
        started = time.monotonic()
        with st.status('入力を確認しています…', expanded=True) as status:
            try:
                if mode == 'ファイル':
                    if len(uploads) > MAX_FILES or sum(f.size for f in uploads) > MAX_TOTAL:
                        raise ValueError('一度に30件・合計300 MBまでです。')
                    for upload in uploads:
                        try:
                            items.append(validate_pdf(upload.name, upload.getvalue()))
                        except Exception as exc:
                            st.session_state.results.append(Result(upload.name, 'failure', error=str(exc)))
                elif mode == 'ZIP':
                    items = read_zip(archive.getvalue())
                else:
                    urls = list(dict.fromkeys(line.strip() for line in url_text.splitlines() if line.strip()))
                    if len(urls) > MAX_FILES:
                        raise ValueError('URLは30件までです。')
                    total_size = 0
                    for index, url in enumerate(urls, 1):
                        st.write(f'URL {index}/{len(urls)} を取得中')
                        try:
                            item = fetch_pdf(url)
                            total_size += len(item.data)
                            if total_size > MAX_TOTAL:
                                raise ValueError('取得したPDFの合計が300 MBを超えました。件数を減らしてください。')
                            items.append(item)
                        except Exception as exc:
                            # Do not persist signed URLs or credentials in the output manifest.
                            # Exception text from HTTP libraries can contain full signed URLs.
                            reason = ('取得がタイムアウトしました。' if isinstance(exc, TimeoutError)
                                      else 'URLの形式・公開アクセス・通信状態・容量制限を確認してください。')
                            st.session_state.results.append(Result(f'URL {index}', 'failure', error=reason))
                        if total_size > MAX_TOTAL:
                            raise ValueError('合計300 MBを超えたため、変換を中止しました。')
                if items:
                    check_batch(items)
                    status.update(label='Doclingを準備しています…')
                    try:
                        converter = get_converter(settings, environment_job.get('log', ''))
                    except Exception as exc:
                        st.session_state.results.extend(
                            Result(item.name, 'failure', error=f'変換器の初期化失敗: {exc}') for item in items
                        )
                        raise
                    progress = st.progress(0, text='変換を開始します')
                    for index, item in enumerate(items, 1):
                        status.update(label=f'変換中 {index}/{len(items)} · {item.name}')
                        result = converter.convert(item)
                        st.session_state.results.append(result)
                        st.write(('✓ ' if result.status == 'success' else '△ ') + item.name)
                        progress.progress(index / len(items), text=f'{index}/{len(items)} 件を処理しました')
                failures = sum(r.status == 'failure' for r in st.session_state.results)
                status.update(label=f'処理完了 · {time.monotonic() - started:.1f}秒 / 失敗 {failures}件',
                              state='error' if failures else 'complete', expanded=False)
            except Exception as exc:
                st.session_state.results.append(Result('バッチ処理', 'failure', error=str(exc)))
                st.error(f'処理を開始・継続できませんでした: {exc}')
                st.caption('モデル取得にはインターネット接続が必要です。OCR依存関係とREADMEのセットアップ手順を確認してください。')
                status.update(label='処理を中断しました', state='error')
