"""HTTP framing checks shared by PDF and dependency downloads."""


def expected_body_length(response) -> int | None:
    getheader = getattr(response, 'getheader', None)
    if getheader is None:
        return None
    # Transfer-Encoding takes precedence over Content-Length.
    transfer = getheader('Transfer-Encoding')
    if transfer and transfer.strip().lower() == 'chunked':
        return None
    value = getheader('Content-Length')
    if value is None:
        return None
    if not value.strip().isascii() or not value.strip().isdecimal():
        raise ValueError('受信サイズのヘッダーが不正です。')
    return int(value)


def verify_body_length(expected: int | None, actual: int) -> None:
    if expected is not None and actual != expected:
        raise ValueError('ダウンロードが途中で切れました。もう一度取得してください。')
