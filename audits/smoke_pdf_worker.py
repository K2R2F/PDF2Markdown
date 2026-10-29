"""Actual Docling inference through the managed worker, using synthetic documents."""
import os
from pathlib import Path
import tempfile
import time

from core.models import Settings
from execution import controller
from storage import state


def text_pdf():
    stream = b'BT /F1 24 Tf 72 700 Td (PDF2Markdown smoke test) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(data)
    data.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(data)


def run_one(name, data, settings, expected):
    start = time.monotonic()
    batch_id = controller.start(settings, 'ファイル', [(name, data)], [], 150)
    while controller.snapshot().get('state') == 'running':
        if time.monotonic() - start > 170:
            controller.cancel(batch_id)
            raise TimeoutError('Smoke test supervisor did not finish')
        time.sleep(0.2)
    _, results, status = state.load_batch(batch_id)
    print(name, status, round(time.monotonic() - start, 2), 'seconds', flush=True)
    for result in results:
        print(result.status, result.error, result.markdown[:300], flush=True)
    assert status == 'complete', controller.snapshot()
    assert len(results) == 1 and results[0].status == 'success', results
    for term in expected:
        assert term in results[0].markdown, (term, results[0].markdown)


if __name__ == '__main__':
    # No model downloads in this test: missing cache must fail rather than silently using the network.
    os.environ['HF_HUB_OFFLINE'] = '1'
    with tempfile.TemporaryDirectory() as folder:
        os.environ['PDF2MARKDOWN_DATA_DIR'] = folder
        run_one('text.pdf', text_pdf(), Settings(ocr_mode='off', tables=False), ['PDF2Markdown'])
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        canvas = Image.new('RGB', (2200, 700), 'white')
        ImageDraw.Draw(canvas).multiline_text((100, 100), '日本語の変換テスト\n会議資料と報告書\nPDF2Markdown',
            fill='black', font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 64), spacing=40)
        output = BytesIO()
        canvas.save(output, format='PDF', resolution=150)
        run_one('scan-ja.pdf', output.getvalue(), Settings(ocr_mode='force', tables=False), ['日本語', '会議'])
