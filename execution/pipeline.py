"""UI-independent batch flow; each completed result is checkpointed."""
from core.models import Result
from core.pdf_validation import MAX_FILES, MAX_TOTAL, validate_pdf, check_batch
from core.zip_input import read_zip
from core.url_input import fetch_pdf
from core.converter import Converter


def run_batch(settings, mode, files, urls, emit, progress):
    results, items = [], []
    def append(result):
        results.append(result)
        emit(results, 'running')
    try:
        if mode == 'URL':
            urls = list(dict.fromkeys(u.strip() for u in urls if u.strip()))
            if not 1 <= len(urls) <= MAX_FILES:
                raise ValueError('URLは1〜30件にしてください。')
            total = 0
            for index, url in enumerate(urls, 1):
                progress(f'URL {index}/{len(urls)} を取得中')
                try:
                    item = fetch_pdf(url)
                    total += len(item.data)
                    if total > MAX_TOTAL:
                        raise ValueError('容量上限')
                    items.append(item)
                except Exception:
                    append(Result(f'URL {index}', 'failure', error='URLの形式・通信・容量制限を確認してください。'))
                if total > MAX_TOTAL:
                    raise ValueError('合計300 MBを超えたため中断しました。')
        elif mode == 'ZIP':
            items = read_zip(files[0][1])
        elif mode == 'ファイル':
            if len(files) > MAX_FILES or sum(len(data) for _, data in files) > MAX_TOTAL:
                raise ValueError('一度に30件・合計300 MBまでです。')
            for name, data in files:
                try:
                    items.append(validate_pdf(name, data))
                except Exception as exc:
                    append(Result(name, 'failure', error=str(exc)))
        else:
            raise ValueError('未対応の入力方法です。')
        if items:
            check_batch(items)
            progress('DoclingとOCRモデルを準備中')
            try:
                converter = Converter(settings)
            except Exception as exc:
                for item in items:
                    append(Result(item.name, 'failure', error=f'変換器の初期化失敗: {exc}'))
                raise
            for index, item in enumerate(items, 1):
                progress(f'変換中 {index}/{len(items)} · {item.name}')
                append(converter.convert(item))
        emit(results, 'failure' if any(r.status == 'failure' for r in results) else 'complete')
    except Exception as exc:
        append(Result('バッチ処理', 'failure', error=str(exc)))
        emit(results, 'failure')
    return results
