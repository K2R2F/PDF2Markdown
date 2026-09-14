from __future__ import annotations

import json
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from core.models import Result, Settings
from core.pdf_validation import safe_name

def output_names(results: list[Result]) -> list[str]:
    used = {'manifest.json'}
    names = []
    for result in results:
        stem = Path(safe_name(result.name)).stem or 'document'
        name = stem + '.md'
        index = 2
        while name.casefold() in used:
            name = f'{stem}_{index}.md'
            index += 1
        used.add(name.casefold())
        names.append(name)
    return names



def make_zip(results: list[Result], settings: Settings) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
        records = []
        for result, name in zip(results, output_names(results)):
            record = asdict(result)
            record.pop('markdown')
            record['output'] = name if result.status != 'failure' else None
            records.append(record)
            if result.status != 'failure':
                archive.writestr(name, result.markdown)
        archive.writestr('manifest.json', json.dumps(
            {'settings': asdict(settings), 'results': records}, ensure_ascii=False, indent=2))
    return buffer.getvalue()
