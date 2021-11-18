from contextlib import contextmanager
from dataclasses import dataclass

import aiohttp
import requests


@dataclass
class EmoRequestInfo:
    """http requestしたデータ"""

    method: str
    url: str
    headers: dict


class EmoPlatformError(Exception):
    """BOCCO emo Platform API利用時のエラー"""

    def __init__(self, message, status=None, request=None):
        self.message = message
        self.status = status
        self.request = request

    def __str__(self):
        return self.message


class EmoHttpError(EmoPlatformError):
    """http request時のエラー"""

    def __str__(self):
        return (
            f"{self.status}, {self.message}, {self.request.method}, {self.request.url}"
        )


class RateLimitError(EmoHttpError):
    """1分あたりのAPI利用回数を上回った場合に出るエラー"""

    pass


class UnauthorizedError(EmoHttpError):
    """API利用に際しての認証エラー"""

    pass


class NotFoundError(EmoHttpError):
    """指定したAPIのURLが存在しない場合に出るエラー"""

    pass


class BadRequestError(EmoHttpError):
    """送るデータの形式が誤っている場合に出るエラー"""

    pass


class UnknownError(EmoHttpError):
    """未定義のエラー"""

    pass


class NoRoomError(EmoPlatformError):
    """BOCCOアカウントに紐づいた部屋がない場合に出るエラー"""

    pass


class TokenError(EmoPlatformError):
    """トークンが正しく設定されてない場合に出るエラー"""

    pass

class UnavailableError(EmoPlatformError):
    """現在のプランでは使用できない場合に出るエラー"""

    def __str__(self):
        return "You can't use this method in " + self.message + " plan."


def _http_status_to_exception(code):
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
def _http_error_handler():
    try:
        yield None
    except requests.HTTPError as e:
        http_exception = _http_status_to_exception(e.response.status_code)
        request = EmoRequestInfo(
            method=e.request.method,
            url=e.request.url,
            headers=e.request.headers,
        )
        raise http_exception(e.response.text, e.response.status_code, request) from e


@contextmanager
def _aiohttp_error_handler(response_msg):
    try:
        yield None
    except aiohttp.ClientResponseError as e:
        http_exception = _http_status_to_exception(e.status)
        request = EmoRequestInfo(
            method=e.request_info.method,
            url=e.request_info.url,
            headers=dict(e.request_info.headers),
        )
        raise http_exception(response_msg, e.status, request) from e
