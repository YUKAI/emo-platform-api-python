from contextlib import contextmanager

import requests


class EmoPlatformError(Exception):
    """BOCCO emo Platform API利用時のエラー"""

    def __init__(self, message):
        self.message = message


class RateLimitError(EmoPlatformError):
    """1分あたり10回のAPI利用回数を上回った場合に出るエラー"""

    pass


class UnauthorizedError(EmoPlatformError):
    """API利用に際しての認証エラー"""

    pass


class NotFoundError(EmoPlatformError):
    """指定したAPIのURLが存在しない場合に出るエラー"""

    pass


class BadRequestError(EmoPlatformError):
    """送るデータの形式が誤っている場合に出るエラー"""

    pass


class UnknownError(EmoPlatformError):
    """未定義のエラー"""

    pass


class NoRoomError(EmoPlatformError):
    """BOCCOアカウントに紐づいた部屋がない場合に出るエラー"""

    pass


class NoRefreshTokenError(EmoPlatformError):
    """リフレッシュトークンが正しく設定されてない場合に出るエラー"""

    pass


def http_status_to_exception(code):
    if code == 400:
        return BadRequestError
    if code == 401:
        return UnauthorizedError
    elif code == 404:
        return NotFoundError
    elif code == 429:
        return RateLimitError
    else:
        return UnknownError


@contextmanager
def http_error_handler():
    try:
        yield None
    except requests.HTTPError as e:
        http_exception = http_status_to_exception(e.response.status_code)
        raise http_exception(e.response.json())
