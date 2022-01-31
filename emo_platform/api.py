import json
import os
from collections import deque
from contextlib import contextmanager
from dataclasses import asdict
from functools import partial
from typing import Callable, Dict, List, NoReturn, Optional, Tuple, Union

import requests

from emo_platform.exceptions import (
    NoRoomError,
    TokenError,
    UnauthorizedError,
    UnavailableError,
    WebhookCallbackError,
    WebhookRequestError,
    _http_error_handler,
)
from emo_platform.models import AccountInfo, BroadcastMsg, Color, Head, Tokens, WebHook
from emo_platform.response import (
    EmoAccountInfo,
    EmoBizAccountInfo,
    EmoBroadcastInfo,
    EmoBroadcastInfoList,
    EmoBroadcastMessage,
    EmoMessageInfo,
    EmoMotionsInfo,
    EmoMsgsInfo,
    EmoRoomInfo,
    EmoRoomSensorInfo,
    EmoSensorsInfo,
    EmoSettingsInfo,
    EmoStampsInfo,
    EmoTokens,
    EmoWebhookBody,
    EmoWebhookInfo,
)

EMO_PLATFORM_PATH = os.path.abspath(os.path.dirname(__file__))


class PostContentType:
    APPLICATION_JSON = "application/json"
    MULTIPART_FORMDATA = None


class TokenManager:
    _TOKEN_FILE = f"{EMO_PLATFORM_PATH}/tokens/emo-platform-api.json"
    _PREVIOUS_TOKEN_FILE = f"{EMO_PLATFORM_PATH}/tokens/emo-platform-api_previous.json"
    _INITIAL_TOKENS = {"access_token": "", "refresh_token": ""}
    _INITIAL_SET_TOKENS = {"os": _INITIAL_TOKENS, "args": _INITIAL_TOKENS}

    def __init__(
        self,
        tokens: Optional[Tokens] = None,
        token_file_path: Optional[str] = None,
        use_cached_credentials=False,
    ):
        self._use_cached_credentials = use_cached_credentials
        if not self._use_cached_credentials:
            self._set_token_file_path(token_file_path)
            self._previous_set_tokens_dict = self._load_previous_set_tokens_file()
            self._current_set_tokens = self._get_current_set_tokens(tokens)
            self._update_previous_set_tokens_file(tokens)
            self.tokens = self._get_latest_tokens()
            self.save_tokens()
        else:
            if tokens:
                self.tokens = tokens
            else:
                raise TokenError(
                    "Please give tokens as an argument using 'emo_platform.Tokens'"
                )

    def _set_token_file_path(self, token_file_path) -> None:
        if token_file_path:
            self._TOKEN_FILE = f"{token_file_path}/emo-platform-api.json"
            self._PREVIOUS_TOKEN_FILE = (
                f"{token_file_path}/emo-platform-api_previous.json"
            )

    def _get_current_set_tokens(self, tokens: Optional[Tokens]) -> Tokens:
        if tokens:
            return tokens
        else:
            return self._get_current_os_env_tokens()

    def _get_current_os_env_tokens(self) -> Tokens:
        access_token = self._get_currnet_os_env_access_token()
        refresh_token = self._get_currnet_os_env_refresh_token()
        return Tokens(**{"refresh_token": refresh_token, "access_token": access_token})  # type: ignore

    def _get_currnet_os_env_access_token(self) -> str:
        try:
            return os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"]
        except KeyError:
            return self._previous_set_tokens_dict["os"]["access_token"]

    def _get_currnet_os_env_refresh_token(self) -> str:
        try:
            return os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"]
        except KeyError:
            return self._previous_set_tokens_dict["os"]["refresh_token"]

    def _load_previous_set_tokens_file(self) -> dict:
        try:
            with open(self._PREVIOUS_TOKEN_FILE) as f:
                return json.load(f)
        except FileNotFoundError:
            return self._INITIAL_SET_TOKENS

    def _update_previous_set_tokens_file(self, tokens) -> None:
        how2set = "os" if tokens is None else "args"
        self._previous_set_tokens = Tokens(**self._previous_set_tokens_dict[how2set])  # type: ignore
        self._previous_set_tokens_dict[how2set] = asdict(self._current_set_tokens)

        with open(self._PREVIOUS_TOKEN_FILE, "w") as f:
            json.dump(self._previous_set_tokens_dict, f)

    def _get_latest_tokens(self) -> Tokens:
        # compare new set tokens with old ones
        if self._current_set_tokens == self._previous_set_tokens:
            try:
                with open(self._TOKEN_FILE) as f:
                    return Tokens(**json.load(f))  # type: ignore
            except FileNotFoundError:
                return self._current_set_tokens
        else:  # reset json file when set tokens updated
            return self._current_set_tokens

    def save_tokens(self) -> None:
        if not self._use_cached_credentials:
            with open(self._TOKEN_FILE, "w") as f:
                json.dump(asdict(self.tokens), f)


class Client:
    """各種apiを呼び出す同期版のclient(Personal版)

    Parameters
    ----------
    endpoint_url : str, default https://platform-api.bocco.me
        BOCCO emo platform apiにアクセスするためのendpoint

    tokens : Tokens, default None
        refresh token及びaccess tokenを指定します。

        指定しない場合は、環境変数に設定されているあるいはこのpkg内のファイル(emo-platform-api.json)に保存されているトークンが使用されます。

    token_file_path : Optional[str], default None
        refresh token及びaccess tokenを保存するファイルのパス。
        指定した場合には指定したパスに、指定しない場合はこのpkg内のディレクトリに、以下の2種類のファイルが生成されます。
            emo-platform-api.json
                最新のトークンを保存するファイル。
            emo-platform-api_previous.json
                前回、引数として指定されたトークンと環境変数として設定されていたトークンが記録されたファイル。

                アクセストークンあるいはリフレッシュトークンの指定が変更された場合(BOCCOアカウントの切り替えを行いたい場合など)に、前回から更新があったかを確認するのに使用されます。

                更新があった場合は、emo-platform-api.jsonに保存されているトークンが上書きされます。

    use_cached_credentials : bool, default False
        Trueにした場合、上述した2つのファイルにrefresh token及びaccess tokenを保存しなくなります。

        この時、引数tokensにトークン情報を与えるようにしてください。(与えない場合は、例外が出されます。)

        この引数をTrueにするのは、サーバーサイドのwebアプリにこのライブラリを使用する際などを想定しています。

    Raises
    ----------
    TokenError
        refresh tokenあるいはaccess tokenが環境変数として設定されていない場合。
        引数tokensにトークンを指定している時は出ません。

    Note
    ----
    各メソッドの実行時にaccess tokenの期限が切れていた場合
        emo-platform-api.jsonに保存されているrefresh tokenを使用して自動的にaccess tokenが更新されます。
        その際にAPI呼び出しが1回行われます。

    Business版をお使いの方へ
        このクラスは使用せずに、継承先である :class:`BizBasicClient` あるいは :class:`BizAdvancedClient` をお使いください。

    """

    _BASE_URL = "https://platform-api.bocco.me"
    _DEFAULT_ROOM_ID = ""
    _MAX_SAVED_REQUEST_ID = 10
    _PLAN = "Personal"

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        tokens: Optional[Tokens] = None,
        token_file_path: Optional[str] = None,
        use_cached_credentials: bool = False,
    ):
        self._tm = TokenManager(
            tokens=tokens, token_file_path=token_file_path, use_cached_credentials=use_cached_credentials
        )
        self._endpoint_url = endpoint_url if endpoint_url else self._BASE_URL
        self._headers: Dict[str, Optional[str]] = {
            "accept": "*/*",
            "Content-Type": PostContentType.APPLICATION_JSON,
            "Authorization": "Bearer " + self._tm.tokens.access_token,
        }
        self._webhook_events_cb: Dict[str, Dict[str, Callable]] = {}
        self._request_id_deque: deque = deque([], self._MAX_SAVED_REQUEST_ID)

    @contextmanager
    def _add_apikey2header(self, api_key: str):
        self._headers["X-Channel-User"] = api_key
        yield
        self._headers.pop("X-Channel-User")

    def _update_tokens(self) -> None:
        """トークンの更新と保存

            jsonファイルに保存されているrefresh tokenを用いて、
            refresh tokenとaccess tokenを更新、jsonファイルに保存します。

            access tokenが切れると自動で呼び出されるため、基本的に外部から使用することはありません。

        Raises
        ----------
        TokenError
            refresh tokenが間違っている場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/oauth/token/refresh

        API呼び出し回数
            1回
        """

        try:
            res_tokens = self.get_access_token(self._tm.tokens.refresh_token)
        except UnauthorizedError as e:
            raise TokenError(
                "Please set refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN' or give args to client using emo_platform.Tokens"
            ) from e
        else:
            self._tm.tokens.access_token = res_tokens.access_token
            self._tm.tokens.refresh_token = res_tokens.refresh_token
            self._headers["Authorization"] = "Bearer " + self._tm.tokens.access_token
            self._tm.save_tokens()
            return

    def _check_http_error(self, request: Callable, _update_tokens: bool = True) -> dict:
        response = request()
        try:
            with _http_error_handler():
                response.raise_for_status()
        except UnauthorizedError:
            if not _update_tokens:
                raise
        else:
            return response.json()

        self._update_tokens()
        response = request()
        with _http_error_handler():
            response.raise_for_status()
        return response.json()

    def _get(self, path: str, params: dict = {}) -> dict:
        request = partial(
            requests.get,
            self._endpoint_url + path,
            params=params,
            headers=self._headers,
        )
        return self._check_http_error(request)

    def _post(
        self,
        path: str,
        data: str = "",
        files: Optional[dict] = None,
        content_type: Optional[str] = PostContentType.APPLICATION_JSON,
        _update_tokens: bool = True,
    ) -> dict:
        self._headers["Content-Type"] = content_type
        request = partial(
            requests.post,
            self._endpoint_url + path,
            data=data,
            files=files,
            headers=self._headers,
        )
        return self._check_http_error(request, _update_tokens=_update_tokens)

    def _put(self, path: str, data: str = "{}") -> dict:
        request = partial(
            requests.put, self._endpoint_url + path, data=data, headers=self._headers
        )
        return self._check_http_error(request)

    def _delete(self, path: str) -> dict:
        request = partial(
            requests.delete, self._endpoint_url + path, headers=self._headers
        )
        return self._check_http_error(request)

    def get_access_token(self, refresh_token: str) -> EmoTokens:
        """トークンの取得

            refresh_tokenを用いて、refresh tokenとaccess tokenを取得します。

        Parameters
        ----------
        refresh_token : str
            refresh tokenとaccess tokenを取得するのに用いるrefresh token。

        Returns
        -------
        emo_tokens : EmoTokens

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/oauth/token/refresh

        API呼び出し回数
            1回

        """

        if refresh_token == "":
            raise TokenError(
                "Please set refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN' or give args to client using emo_platform.Tokens"
            )
        payload = {"refresh_token": refresh_token}
        response = self._post(
            "/oauth/token/refresh", json.dumps(payload), _update_tokens=False
        )
        return EmoTokens(**response)

    def _get_account_info(self) -> dict:
        return self._get("/v1/me")

    def get_account_info(
        self,
    ) -> EmoAccountInfo:
        """アカウント情報の取得

        Returns
        -------
        account_info : EmoAccountInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/me

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get_account_info()
        return EmoAccountInfo(**response)

    def delete_account_info(
        self,
    ) -> EmoAccountInfo:
        """アカウントの削除

            紐づくWebhook等の設定も全て削除されます。

        Returns
        -------
        account_info : EmoAccountInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#delete-/v1/me

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._delete("/v1/me")
        return EmoAccountInfo(**response)

    def get_rooms_list(self) -> EmoRoomInfo:
        """ユーザが参加している部屋の一覧の取得

        Returns
        -------
        rooms_list : EmoRoomInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get("/v1/rooms")
        return EmoRoomInfo(**response)

    def get_rooms_id(self) -> List[str]:
        """ユーザーが参加している全ての部屋のidの取得

        Returns
        -------
        rooms_id : List[str]
            取得した部屋のidのリスト

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合
            あるいは、ユーザーが参加している部屋が1つもなかった場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        rooms_info = self.get_rooms_list()
        return self._get_rooms_id(rooms_info)

    def _get_rooms_id(self, rooms_info: EmoRoomInfo) -> List[str]:
        try:
            room_number = len(rooms_info.rooms)
        except KeyError:
            raise NoRoomError("Get no room id.")
        if room_number == 0:
            raise NoRoomError("Get no room id.")
        rooms_id = [rooms_info.rooms[i].uuid for i in range(room_number)]
        return rooms_id

    def create_room_client(self, room_id: str):
        """部屋固有の各種apiを呼び出すclientの作成

            部屋のidは、:func:`get_rooms_id` を使用することで、取得できます。

        Parameters
        ----------
        room_id : str
            部屋のid

        Returns
        -------
        room_client : Room
            部屋のclient

        Note
        ----
        API呼び出し回数
            0回

        """

        return Room(self, room_id)

    def get_stamps_list(
        self,
    ) -> EmoStampsInfo:
        """利用可能なスタンプ一覧の取得

        Returns
        -------
        stamps_info : EmoStampsInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/stamps

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get("/v1/stamps")
        return EmoStampsInfo(**response)

    def get_motions_list(
        self,
    ) -> EmoMotionsInfo:
        """利用可能なプリセットモーション一覧の取得

        Returns
        -------
        motions_info : EmoMotionsInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/motions

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get("/v1/motions")
        return EmoMotionsInfo(**response)

    def get_webhook_setting(
        self,
    ) -> EmoWebhookInfo:
        """現在設定されているWebhookの情報の取得

        Returns
        -------
        webhook_info : EmoWebhookInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get("/v1/webhook")
        return EmoWebhookInfo(**response)

    def change_webhook_setting(self, webhook: WebHook) -> EmoWebhookInfo:
        """Webhookの設定の変更

        Parameters
        ----------
        webhook : WebHook
            適用するWebhookの設定。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            変更後のWebhookの設定

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"description": webhook.description, "url": webhook.url}
        response = self._put("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def register_webhook_event(self, events: List[str]) -> EmoWebhookInfo:
        """Webhook通知するイベントの指定

            eventの種類は、
            `こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events>`_
            から確認できます。

        Parameters
        ----------
        events : List[str]
            指定するWebhook event。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            設定したWebhookの情報

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"events": events}
        response = self._put("/v1/webhook/events", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def create_webhook_setting(self, webhook: WebHook) -> EmoWebhookInfo:
        """Webhookの設定の作成

        Parameters
        ----------
        webhook : WebHook
            作成するWebhookの設定。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            作成したWebhookの設定。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"description": webhook.description, "url": webhook.url}
        response = self._post("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def delete_webhook_setting(
        self,
    ) -> EmoWebhookInfo:
        """現在設定されているWebhookの情報の削除

        Returns
        -------
        webhook_info : EmoWebhookInfo
            削除したWebhookの情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#delete-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._delete("/v1/webhook")
        return EmoWebhookInfo(**response)

    def event(
        self, event: str, room_id_list: List[str] = [_DEFAULT_ROOM_ID]
    ) -> Callable:
        """Webhookの指定のeventが通知されたときに呼び出す関数の登録

        Example
        -----
        呼び出したい関数にdecorateして登録します::

            import emo_platform

            client = emo_platform.Client()

            @client.event("message.received")
            def test_event_callback(body):
                print(body)

        Parameters
        ----------
        event : str
            指定するWebhook event。

            eventの種類は、`こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events>`_ から確認できます。

        room_id_list : List[str], default [""]
            指定したWebhook eventの通知を監視する部屋をidで指定できます。

            引数なしだと、全ての部屋を監視します。

        Note
        ----
        API呼び出し回数
            0回

        """

        def decorator(func):

            if event not in self._webhook_events_cb:
                self._webhook_events_cb[event] = {}

            for room_id in room_id_list:
                self._webhook_events_cb[event][room_id] = func

        return decorator

    def start_webhook_event(self) -> str:
        """BOCCO emoのWebhookのイベント通知の開始

            :func:`event` で指定したイベントの通知が開始されます。

            使用する際は、以下の手順を踏んでください。

            1. ngrokなどを用いて、ローカルサーバーにForwardingするURLを発行

            2. :func:`create_webhook_setting` で、1で発行したURLをBOCCO emoに設定

            3. :func:`event` で通知したいeventとそれに対応するcallback関数を設定

            4. この関数を実行

            5. ローカルサーバーを起動し、:func:`get_cb_func` を利用して、webhook通知があった際に対応するcallback関数を実行

        Returns
        -------
        secret_key : str
            BOCCO emoのWebhookリクエストのHTTP Headerに含まれるX-Platform-Api-Secretの値と一致する文字列です。

            第三者からの、予期せぬリクエストを防ぐため、この文字列を利用した認証を実装してください。

        Raises
        ----------
        EmoPlatformError
            関数内部で呼び出している :func:`register_webhook_event` が例外を出した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self.register_webhook_event(list(self._webhook_events_cb.keys()))
        return response.secret

    def get_cb_func(self, body: dict) -> Tuple[Callable, EmoWebhookBody]:
        """受信したwebhookイベントに対応するcallback関数及びパースされたボディの取得

            使用する際は、以下の手順を踏んでください。

            1. ngrokなどを用いて、ローカルサーバーにForwardingするURLを発行

            2. :func:`create_webhook_setting` で、1で発行したURLをBOCCO emoに設定

            3. :func:`event` で通知したいeventとそれに対応するcallback関数を設定

            4. :func:`start_webhook_event` でwebhook通知を開始

            5. ローカルサーバーを起動し、この関数を利用して、webhook通知があった際に対応するcallback関数を実行

        Example
        -----
        python標準ライブラリを使用してローカルサーバーを立てた例::

            import emo_platform, json, http.server

            client = emo_platform.Client()

            client.create_webhook_setting(emo_platform.WebHook("WEBHOOK URL"))

            @client.event("message.received")
            def test_event_callback(body):
                print(body)

            secret_key = client.start_webhook_event()

            class Handler(http.server.BaseHTTPRequestHandler):
                def _send_status(self, status):
                    self.send_response(status)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()

                def do_POST(self):
                    # check secret_key
                    if not secret_key == self.headers["X-Platform-Api-Secret"]:
                        self._send_status(401)

                    content_len = int(self.headers['content-length'])
                    request_body = json.loads(self.rfile.read(content_len).decode('utf-8'))

                    try:
                        cb_func, emo_webhook_body = client.get_cb_func(request_body)
                    except emo_platform.EmoPlatformError:
                        self._send_status(501)
                        return

                    cb_func(emo_webhook_body)

                    self._send_status(200)

            with http.server.HTTPServer(('', 8000), Handler) as httpd:
                httpd.serve_forever()

        Parameters
        ----------
        body : dict
            受信したwebhookリクエストのボディのJSONペイロード

        Returns
        -------
        cb_func, emo_webhook_body : Tuple[Callable, EmoWebhookBody]

        Raises
        ----------
        EmoPlatformError
            受信したwebhookイベントに対応するcallback関数が登録されていない場合。

        Note
        ----
        API呼び出し回数
            0回

        """

        emo_webhook_body = EmoWebhookBody(**body)
        if emo_webhook_body.request_id not in self._request_id_deque:
            try:
                event_cb = self._webhook_events_cb[emo_webhook_body.event]
            except KeyError as e:
                raise WebhookCallbackError("event") from e
            room_id = emo_webhook_body.uuid
            if room_id in event_cb:
                cb_func = event_cb[room_id]
            elif self._DEFAULT_ROOM_ID in event_cb:
                cb_func = event_cb[self._DEFAULT_ROOM_ID]
            else:
                raise WebhookCallbackError("room")
            self._request_id_deque.append(emo_webhook_body.request_id)
            return cb_func, emo_webhook_body
        else:
            raise WebhookRequestError("Webhook request id is duplicated")


class BizClient(Client):
    """各種apiを呼び出す同期版のclient(Business版)

    Note
    ----
    使用上の注意
        このクラスは使用せずに、継承先である :class:`BizBasicClient` あるいは :class:`BizAdvancedClient` をお使いください。
    """

    _PLAN = "Business"

    def get_account_info(self) -> EmoBizAccountInfo:  # type: ignore[override]
        """アカウント情報の取得

        Returns
        -------
        account_info : EmoBizAccountInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        Personal版とBusiness版での違い
            返り値の型が異なるので注意してください。

        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/me

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get_account_info()
        return EmoBizAccountInfo(**response)

    def delete_account_info(self) -> NoReturn:
        """アカウント情報の取得

            Business版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        Note
        ----
        Personal版とBusiness版での違い
            Business版では使用できません。

        """

        raise UnavailableError(self._PLAN)

    def change_account_info(self, acount: AccountInfo) -> EmoBizAccountInfo:
        """アカウント情報の編集

        Parameters
        ----------
        account : AccountInfo
            新たなアカウント情報。

        Returns
        -------
        account_info : EmoBizAccountInfo
            編集後のアカウント情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/me

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = asdict(acount)
        response = self._put("/v1/me", json.dumps(payload))
        return EmoBizAccountInfo(**response)

    def get_rooms_list(self, api_key: str) -> EmoRoomInfo:  # type: ignore[override]
        """ユーザが参加している部屋の一覧の取得

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        Returns
        -------
        rooms_list : EmoRoomInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().get_rooms_list()

    def get_rooms_id(self, api_key: str) -> List[str]:  # type: ignore[override]
        """ユーザーが参加している全ての部屋のidの取得

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        Returns
        -------
        rooms_id : List[str]
            取得した部屋のidのリスト

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合
            あるいは、ユーザーが参加している部屋が1つもなかった場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        rooms_info = self.get_rooms_list(api_key)
        return self._get_rooms_id(rooms_info)

    def get_stamps_list(self, api_key: str) -> EmoStampsInfo:  # type: ignore[override]
        """利用可能なスタンプ一覧の取得

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        Returns
        -------
        stamps_info : EmoStampsInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/stamps

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().get_stamps_list()

    def get_broadcast_msgs_list(self) -> EmoBroadcastInfoList:
        """配信メッセージの一覧の取得

        Returns
        -------
        broadcast_info_list : EmoBroadcastInfoList
            配信メッセージの一覧。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/broadcast_messages

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get("/v1/broadcast_messages")
        return EmoBroadcastInfoList(**response)

    def get_broadcast_msg_details(self, message_id: int) -> EmoBroadcastInfo:
        """配信メッセージの詳細の取得

        Parameters
        ----------
        message_id : int
            詳細を取得したい配信メッセージのid

        Returns
        -------
        broadcast_info_list : EmoBroadcastInfo
            配信メッセージの詳細。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/broadcast_messages/-broadcast_message_id-

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._get("/v1/broadcast_messages/" + str(message_id))
        return EmoBroadcastInfo(**response)

    def create_broadcast_msg(
        self, api_key: str, message: BroadcastMsg
    ) -> EmoBroadcastMessage:
        """配信メッセージの新規作成

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        message : BroadcastMsg
            新規に作成する配信メッセージ。

        Returns
        -------
        broadcast_msg : EmoBroadcastMessage
            新規に作成した配信メッセージの内容。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/broadcast_messages

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = asdict(message)
        if message.immediate:
            payload.pop("executed_at")
        with self._add_apikey2header(api_key):
            response = self._post("/v1/broadcast_messages", json.dumps(payload))
        return EmoBroadcastMessage(**response)


class BizBasicClient(BizClient):
    """各種apiを呼び出す同期版のclient(Business Basic版)

    Parameters
    ----------
    endpoint_url : str, default https://platform-api.bocco.me
        BOCCO emo platform apiにアクセスするためのendpoint

    tokens : Tokens, default None
        refresh token及びaccess tokenを指定します。

        指定しない場合は、環境変数に設定されているあるいはこのpkg内のファイル(emo-platform-api.json)に保存されているトークンが使用されます。
    token_file_path : Optional[str], default None
        refresh token及びaccess tokenを保存するファイルのパス。

        指定しない場合は、このpkg内のディレクトリに保存されます。
        指定したパスには、以下の2種類のファイルが生成されます。
            emo-platform-api.json
                最新のトークンを保存するファイル。
            emo-platform-api_previous.json
                前回、引数として指定されたトークンと環境変数として設定されていたトークンが記録されたファイル。

                アクセストークンあるいはリフレッシュトークンの指定が変更された場合(BOCCOアカウントの切り替えを行いたい場合など)に、前回から更新があったかを確認するのに使用されます。

                更新があった場合は、emo-platform-api.jsonに保存されているトークンが上書きされます。
    Raises
    ----------
    TokenError
        refresh tokenあるいはaccess tokenが環境変数として設定されていない場合。
        引数tokensにトークンを指定している時は出ません。

    Note
    ----
    各メソッドの実行時にaccess tokenの期限が切れていた場合
        emo-platform-api.jsonに保存されているrefresh tokenを使用して自動的にaccess tokenが更新されます。
        その際にAPI呼び出しが1回行われます。

    """

    _PLAN = "Business Basic"

    def create_room_client(self, api_key: str, room_id: str):  # type: ignore[override]
        """部屋固有の各種apiを呼び出すclientの作成

            部屋のidは、:func:`get_rooms_id` を使用することで、取得できます。

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        room_id : str
            部屋のid

        Returns
        -------
        room_client : BizBasicRoom
            部屋のclient

        Note
        ----
        API呼び出し回数
            0回

        """

        return BizBasicRoom(self, room_id, api_key)

    def get_motions_list(self) -> NoReturn:
        """利用可能なプリセットモーション一覧の取得

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def get_webhook_setting(self, api_key: str) -> NoReturn:  # type: ignore[override]
        """現在設定されているWebhookの情報の取得

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def change_webhook_setting(self, api_key: str, webhook: WebHook) -> NoReturn:  # type: ignore[override]
        """Webhookの設定の変更

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def register_webhook_event(self, api_key: str, events: List[str]) -> NoReturn:  # type: ignore[override]
        """Webhook通知するイベントの指定

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def create_webhook_setting(self, api_key: str, webhook: WebHook) -> NoReturn:  # type: ignore[override]
        """Webhookの設定の作成

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def delete_webhook_setting(self, api_key: str) -> NoReturn:  # type: ignore[override]
        """現在設定されているWebhookの情報の削除

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def event(
        self, event: str, room_id_list: List[str] = [Client._DEFAULT_ROOM_ID]
    ) -> NoReturn:
        """Webhookの指定のeventが通知されたときに呼び出す関数の登録

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def start_webhook_event(self) -> NoReturn:
        """BOCCO emoのWebhookのイベント通知の開始

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)

    def get_cb_func(self, body: dict) -> NoReturn:
        """受信したwebhookイベントに対応するcallback関数及びパースされたボディの取得

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._PLAN)


class BizAdvancedClient(BizClient):
    """各種apiを呼び出す同期版のclient(Business Advanced版)

    Parameters
    ----------
    endpoint_url : str, default https://platform-api.bocco.me
        BOCCO emo platform apiにアクセスするためのendpoint

    tokens : Tokens, default None
        refresh token及びaccess tokenを指定します。

        指定しない場合は、環境変数に設定されているあるいはこのpkg内のファイル(emo-platform-api.json)に保存されているトークンが使用されます。
    token_file_path : Optional[str], default None
        refresh token及びaccess tokenを保存するファイルのパス。

        指定しない場合は、このpkg内のディレクトリに保存されます。
        指定したパスには、以下の2種類のファイルが生成されます。
            emo-platform-api.json
                最新のトークンを保存するファイル。
            emo-platform-api_previous.json
                前回、引数として指定されたトークンと環境変数として設定されていたトークンが記録されたファイル。

                アクセストークンあるいはリフレッシュトークンの指定が変更された場合(BOCCOアカウントの切り替えを行いたい場合など)に、前回から更新があったかを確認するのに使用されます。

                更新があった場合は、emo-platform-api.jsonに保存されているトークンが上書きされます。
    Raises
    ----------
    TokenError
        refresh tokenあるいはaccess tokenが環境変数として設定されていない場合。
        引数tokensにトークンを指定している時は出ません。

    Note
    ----
    各メソッドの実行時にaccess tokenの期限が切れていた場合
        emo-platform-api.jsonに保存されているrefresh tokenを使用して自動的にaccess tokenが更新されます。
        その際にAPI呼び出しが1回行われます。

    """

    _PLAN = "Business Advanced"

    def create_room_client(self, api_key: str, room_id: str):  # type: ignore[override]
        """部屋固有の各種apiを呼び出すclientの作成

            部屋のidは、:func:`get_rooms_id` を使用することで、取得できます。

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        room_id : str
            部屋のid

        Returns
        -------
        room_client : BizAdvancedRoom
            部屋のclient

        Note
        ----
        API呼び出し回数
            0回

        """

        return BizAdvancedRoom(self, room_id, api_key)

    def get_webhook_setting(  # type: ignore[override]
        self,
        api_key: str,
    ) -> EmoWebhookInfo:
        """現在設定されているWebhookの情報の取得

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        Returns
        -------
        webhook_info : EmoWebhookInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().get_webhook_setting()

    def change_webhook_setting(self, api_key: str, webhook: WebHook) -> EmoWebhookInfo:  # type: ignore[override]
        """Webhookの設定の変更

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        webhook : WebHook
            適用するWebhookの設定。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            変更後のWebhookの設定

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().change_webhook_setting(webhook)

    def register_webhook_event(self, api_key: str, events: List[str]) -> EmoWebhookInfo:  # type: ignore[override]
        """Webhook通知するイベントの指定

            eventの種類は、
            `こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events>`_
            から確認できます。

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        events : List[str]
            指定するWebhook event。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            設定したWebhookの情報

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().register_webhook_event(events)

    def create_webhook_setting(self, api_key: str, webhook: WebHook) -> EmoWebhookInfo:  # type: ignore[override]
        """Webhookの設定の作成

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        webhook : WebHook
            作成するWebhookの設定。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            作成したWebhookの設定。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().create_webhook_setting(webhook)

    def delete_webhook_setting(self, api_key: str) -> EmoWebhookInfo:  # type: ignore[override]
        """現在設定されているWebhookの情報の削除

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        Returns
        -------
        webhook_info : EmoWebhookInfo
            削除したWebhookの情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#delete-/v1/webhook

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with self._add_apikey2header(api_key):
            return super().delete_webhook_setting()

    def start_webhook_event(self, api_key: str) -> str:  # type: ignore[override]
        """BOCCO emoのWebhookのイベント通知の開始

            :func:`event` で指定したイベントの通知が開始されます。

            使用する際は、以下の手順を踏んでください。

            1. ngrokなどを用いて、ローカルサーバーにForwardingするURLを発行

            2. :func:`create_webhook_setting` で、1で発行したURLをBOCCO emoに設定

            3. :func:`event` で通知したいeventとそれに対応するcallback関数を設定

            4. この関数を実行

            5. ローカルサーバーを起動し、 :func:`get_cb_func` を利用して、webhook通知があった際に対応するcallback関数を実行

        Parameters
        ----------
        api_key : str
            法人向けAPIキー

            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認することができます。

        Returns
        -------
        secret_key : str
            BOCCO emoのWebhookリクエストのHTTP Headerに含まれるX-Platform-Api-Secretの値と一致する文字列です。

            第三者からの、予期せぬリクエストを防ぐため、この文字列を利用した認証を実装してください。

        Raises
        ----------
        EmoPlatformError
            関数内部で呼び出している :func:`register_webhook_event` が例外を出した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self.register_webhook_event(
            api_key, list(self._webhook_events_cb.keys())
        )
        return response.secret


class Room:
    """部屋固有の各種apiを呼び出す同期版のclient

    Parameters
    ----------
    base_client : Client
        このclientを作成しているclient。

    room_id : str
        部屋のuuid。

    """

    def __init__(self, base_client: Client, room_id: str):
        self._base_client = base_client
        self.room_id = room_id

    def get_msgs(self, ts: int = None) -> EmoMsgsInfo:
        """部屋に投稿されたメッセージの取得

        Parameters
        ----------
        ts : int or None
            指定した場合は、その時刻以前のメッセージを取得できます。

                指定方法：2021/07/01 12:30:45以前なら、20210701123045000

        Returns
        -------
        response : EmoMsgsInfo
            投稿されたメッセージの情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/messages

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        params = {"before": ts} if ts else {}
        response = self._base_client._get(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )
        return EmoMsgsInfo(**response)

    def get_sensors_list(
        self,
    ) -> EmoSensorsInfo:
        """BOCCO emoとペアリングされているセンサの一覧の取得

            センサの種類は
            `こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/sensors>`_
            で確認できます。

        Returns
        -------
        sensors_info : EmoSensorsInfo
            取得した設定値。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/sensors

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._base_client._get("/v1/rooms/" + self.room_id + "/sensors")
        return EmoSensorsInfo(**response)

    def get_sensor_values(self, sensor_id: str) -> EmoRoomSensorInfo:
        """部屋センサの送信値を取得

        Parameters
        ----------
        sensor_id : str
            部屋センサのuuid。

            各部屋センサのuuidは、:func:`get_sensors_list` で確認できます。

        Returns
        -------
        response : EmoRoomSensorInfo
            部屋センサの送信値の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (部屋センサ以外のBOCCOセンサ / 紐づいていない部屋センサ、のidを指定した場合も含みます)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/sensors/-sensor_uuid-/values

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._base_client._get(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )
        return EmoRoomSensorInfo(**response)

    def send_audio_msg(self, audio_data_path: str) -> EmoMessageInfo:
        """音声ファイルの部屋への投稿

        Attention
        ----
        送信できるファイルの制限について
            フォーマット:    MP3, M4A

            ファイルサイズ:  1MB

        Parameters
        ----------
        audio_data_path : str
            投稿する音声ファイルの絶対パス。

        Returns
        -------
        response : EmoMessageInfo
            音声ファイル投稿時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/audio

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with open(audio_data_path, "rb") as audio_data:
            files = {"audio": audio_data}
            response = self._base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    def send_image(self, image_data_path: str) -> EmoMessageInfo:
        """画像ファイルの部屋への投稿

        Attention
        ----
        送信できるファイルの制限について
            フォーマット:    JPG, PNG

            ファイルサイズ:  1MB

        Parameters
        ----------
        image_data_path : str
            投稿する画像ファイルの絶対パス。

        Returns
        -------
        response : EmoMessageInfo
            画像投稿時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/image

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        with open(image_data_path, "rb") as image_data:
            files = {"image": image_data}
            response = self._base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/image",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    def send_msg(self, msg: str) -> EmoMessageInfo:
        """テキストメッセージの部屋への投稿

        Parameters
        ----------
        msg : str
            投稿するメッセージ。

        Returns
        -------
        response : EmoMessageInfo
            メッセージ投稿時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/text

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"text": msg}
        response = self._base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_stamp(self, stamp_id: str, msg: Optional[str] = None) -> EmoMessageInfo:
        """スタンプの部屋への投稿

        Parameters
        ----------
        stamp_id : str
            スタンプのuuid。

            各スタンプのuuidは、:func:`Client.get_stamps_list` で確認できます。

        msg : Optional[str], default None
            スタンプ投稿時に、BOCCO emoが行うモーション再生と共に発話されるメッセージ。

            引数なしの場合は、発話なしでモーションが再生されます。

        Returns
        -------
        response : EmoMessageInfo
            スタンプモーション送信時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/stamp

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        response = self._base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_original_motion(self, motion_data: Union[str, dict]) -> EmoMessageInfo:
        """独自定義した、オリジナルのモーションをBOCCO emoに送信

            詳しくは、
            `こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions>`_
            を参照してください。

        Parameters
        ----------
        motion_data : str or dict
            モーションファイルを置いている絶対パス。

            あるいは、モーションを記述した辞書オブジェクト。

        Returns
        -------
        response : EmoMessageInfo
            モーション送信時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。
            (モーションのデータ形式が誤っている場合も含みます)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        if type(motion_data) == str:
            with open(motion_data) as f:
                payload = json.load(f)
        else:
            payload = motion_data
        response = self._base_client._post(
            "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def change_led_color(self, color: Color) -> EmoMessageInfo:
        """ほっぺたの色の変更

            3秒間、ほっぺたの色を指定した色に変更します。

        Parameters
        ----------
        color : Color
            送信するほっぺたの色。

        Returns
        -------
        response : EmoMessageInfo
            モーション送信時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions/led_color

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        response = self._base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def move_to(self, head: Head) -> EmoMessageInfo:
        """首の角度の変更

            首の角度を変更するモーションをBOCCO emoに送信します。

        Parameters
        ----------
        head : Head
            送信する首の角度。

        Returns
        -------
        response : EmoMessageInfo
            モーション送信時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions/move_to

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        response = self._base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_motion(self, motion_id: str) -> EmoMessageInfo:
        """プリセットモーションをBOCCO emoに送信

        Parameters
        ----------
        motion_id : str
            プリセットモーションのuuid

            各プリセットモーションのuuidは、:func:`Client.get_motions_list` で確認できます。

        Returns
        -------
        response : EmoMessageInfo
            モーション送信時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions/preset

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"uuid": motion_id}
        response = self._base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def get_emo_settings(
        self,
    ) -> EmoSettingsInfo:
        """現在のBOCCO emoの設定値を取得

        Returns
        -------
        settings : EmoSettingsInfo
            取得した設定値。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているAPI呼び出しが失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/emo/settings

        API呼び出し回数
            1回 + 1回(access tokenが切れていた場合)

        """

        response = self._base_client._get("/v1/rooms/" + self.room_id + "/emo/settings")
        return EmoSettingsInfo(**response)


class BizRoom(Room):
    """部屋固有の各種apiを呼び出す同期版のclient(Business版)

    Parameters
    ----------
    base_client : BizClient
        このclientを作成しているclient。

    room_id : str
        部屋のuuid。

    api_key : str
        法人向けAPIキー

        法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
        から確認することができます。

    """

    def __init__(self, base_client: Client, room_id: str, api_key: str):
        super().__init__(base_client=base_client, room_id=room_id)
        self.api_key = api_key

    def get_msgs(self, ts: int = None) -> EmoMsgsInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().get_msgs(ts)

    def get_sensors_list(
        self,
    ) -> EmoSensorsInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().get_sensors_list()

    def send_audio_msg(self, audio_data_path: str) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().send_audio_msg(audio_data_path)

    def send_image(self, image_data_path: str) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().send_image(image_data_path)

    def send_msg(self, msg: str) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().send_msg(msg)

    def send_stamp(self, stamp_id: str, msg: Optional[str] = None) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().send_stamp(stamp_id, msg)

    def get_emo_settings(
        self,
    ) -> EmoSettingsInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().get_emo_settings()


class BizBasicRoom(BizRoom):
    """部屋固有の各種apiを呼び出す同期版のclient(Business Basic版)

    Parameters
    ----------
    base_client : BizBasicClient
        このclientを作成しているclient。

    room_id : str
        部屋のuuid。

    api_key : str
        法人向けAPIキー

        法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
        から確認することができます。

    """

    def get_sensor_values(self, sensor_id: str) -> NoReturn:
        """部屋センサの送信値を取得

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._base_client._PLAN)

    def send_original_motion(self, motion_data: Union[str, dict]) -> NoReturn:
        """独自定義した、オリジナルのモーションをBOCCO emoに送信

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._base_client._PLAN)

    def change_led_color(self, color: Color) -> NoReturn:
        """ほっぺたの色の変更

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._base_client._PLAN)

    def move_to(self, head: Head) -> NoReturn:
        """首の角度の変更

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._base_client._PLAN)

    def send_motion(self, motion_id: str) -> NoReturn:
        """プリセットモーションをBOCCO emoに送信

            Business Basic版では使用できないメソッドです。

        Raises
        ----------
        UnavailableError
            この関数を呼び出した場合。

        """

        raise UnavailableError(self._base_client._PLAN)


class BizAdvancedRoom(BizRoom):
    """部屋固有の各種apiを呼び出す同期版のclient(Business Advanced版)

    Parameters
    ----------
    base_client : BizAdvancedClient
        このclientを作成しているclient。

    room_id : str
        部屋のuuid。

    api_key : str
        法人向けAPIキー

        法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
        から確認することができます。

    """

    def get_sensor_values(self, sensor_id: str) -> EmoRoomSensorInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().get_sensor_values(sensor_id)

    def send_original_motion(self, motion_data: Union[str, dict]) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().send_original_motion(motion_data)

    def change_led_color(self, color: Color) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().change_led_color(color)

    def move_to(self, head: Head) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().move_to(head)

    def send_motion(self, motion_id: str) -> EmoMessageInfo:
        with self._base_client._add_apikey2header(self.api_key):
            return super().send_motion(motion_id)
