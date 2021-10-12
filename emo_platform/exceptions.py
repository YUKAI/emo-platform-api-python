from contextlib import contextmanager
from dataclasses import dataclass
import aiohttp
import requests

@dataclass
class EmoRequestInfo:
    method: str
    url   : str
    headers : dict


class EmoPlatformError(Exception):
    def __init__(self, message):
        self.message = message


class EmoHttpError(EmoPlatformError):
    def __init__(self, message, status, request):
        self.message = message
        self.status = status
        self.request = request

    def __str__(self):
        return f"{self.status}, {self.message}, {self.request.method}, {self.request.url}"


class RateLimitError(EmoHttpError):
    pass


class UnauthorizedError(EmoHttpError):
    pass


class NotFoundError(EmoHttpError):
    pass


class BadRequestError(EmoHttpError):
    pass


class UnknownError(EmoHttpError):
    pass


class NoRoomError(EmoPlatformError):
    pass


class NoRefreshTokenError(EmoPlatformError):
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
        request = EmoRequestInfo(
            method=e.request.method,
            url=e.request.url,
            headers=e.request.headers,
        )
        raise http_exception(e.response.text, e.response.status_code, request)


@contextmanager
def aiohttp_error_handler(response_msg):
    try:
        yield None
    except aiohttp.ClientResponseError as e:
        http_exception = http_status_to_exception(e.status)
        request = EmoRequestInfo(
            method=e.request_info.method,
            url=e.request_info.url,
            headers=dict(e.request_info.headers),
        )
        raise http_exception(response_msg, e.status, request)
