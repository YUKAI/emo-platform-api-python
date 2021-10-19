import json
import os
from collections import deque
from functools import partial
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import requests
import uvicorn  # type: ignore
from fastapi import BackgroundTasks, FastAPI, Request

from emo_platform.exceptions import (
    NoRoomError,
    TokenError,
    UnauthorizedError,
    _http_error_handler,
)
from emo_platform.models import Color, Head, WebHook
from emo_platform.response import (
    EmoAccountInfo,
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
    """POSTするデータの種類"""

    APPLICATION_JSON = "application/json"
    MULTIPART_FORMDATA = None


class Client:
    """各種apiを呼び出す同期版のclient

    Parameters
    ----------
    endpoint_url : str, default https://platform-api.bocco.me
        BOCCO emo platform apiにアクセスするためのendpoint

    token_file_path : Optional[str], default None
        refresh token及びaccess tokenを保存するファイルのパス。

        指定しない場合は、このpkg内のディレクトリに保存されます。

        指定したパスには、以下の2種類のファイルが生成されます。

            emo-platform-api.json
                最新のトークンを保存するファイル

            emo-platform-api_previous.json
                現在、環境変数として設定されているトークンを保存するファイル

                前回との差分検知のために使用されます。

                差分があった場合は、emo-platform-api.jsonに保存されているトークンが削除されます。

    Raises
    ----------
    NoRefreshTokenError
        refresh tokenあるいはaccess tokenが環境変数として設定されていないもしくは間違っている場合。

    RateLimitError
        APIをレートリミットを超えて呼び出した場合。

    Note
    ----
    使用しているaccess tokenの期限が切れた場合
        refresh tokenをもとに自動的に更新されます。

        その際にAPI呼び出しが最大で2回行われます。

        refresh tokenは以下の優先順位で選ばれます。

        1. emo-platform-api.jsonに保存されているrefresh token

        2. 環境変数 EMO_PLATFORM_API_REFRESH_TOKENに設定されているrefresh token

        ただし、emo-platform-api_previous.jsonに差分があった場合は、1はskipされるようになっています。

        clientの各メソッドを実行した際も、access tokenが切れていた場合、同様に自動更新が行われます。

    """

    _BASE_URL = "https://platform-api.bocco.me"
    _TOKEN_FILE = f"{EMO_PLATFORM_PATH}/tokens/emo-platform-api.json"
    _PREVOIUS_TOKEN_FILE = f"{EMO_PLATFORM_PATH}/tokens/emo-platform-api_previous.json"
    _DEFAULT_ROOM_ID = ""
    _MAX_SAVED_REQUEST_ID = 10

    def __init__(
        self, endpoint_url: str = _BASE_URL, token_file_path: Optional[str] = None
    ):
        if token_file_path is not None:
            self._TOKEN_FILE = f"{token_file_path}/emo-platform-api.json"
            self._PREVOIUS_TOKEN_FILE = (
                f"{token_file_path}/emo-platform-api_previous.json"
            )
        self.endpoint_url = endpoint_url
        self.headers: Dict[str, Optional[str]] = {
            "accept": "*/*",
            "Content-Type": PostContentType.APPLICATION_JSON,
        }

        # load prevoius os env tokens
        try:
            with open(self._PREVOIUS_TOKEN_FILE) as f:
                prevoius_env_tokens = json.load(f)
        except FileNotFoundError:
            prevoius_env_tokens = {"refresh_token": "", "access_token": ""}

        # get current os env access token
        try:
            access_token = os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"]
        except KeyError as e:
            # try to use old prevoius os env access token when current one doesn't exsist
            if (prevoius_env_tokens["access_token"]) == "":
                raise TokenError("set tokens as 'EMO_PLATFORM_API_ACCESS_TOKEN'") from e
            else:
                access_token = prevoius_env_tokens["access_token"]

        # get current os env refresh token
        try:
            refresh_token = os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"]
        except KeyError as e:
            # try to use old prevoius os env refresh token when current one doesn't exsist
            if (prevoius_env_tokens["refresh_token"]) == "":
                raise TokenError("set tokens as 'EMO_PLATFORM_API_REFRESH_TOKEN'") from e
            else:
                refresh_token = prevoius_env_tokens["refresh_token"]

        self.current_env_tokens = {
            "refresh_token" : refresh_token,
            "access_token" : access_token
        }

        # save new os env tokens
        with open(self._PREVOIUS_TOKEN_FILE, "w") as f:
            json.dump(self.current_env_tokens, f)

        # compare new os env tokens with old ones
        if self.current_env_tokens == prevoius_env_tokens:
            try:
                with open(self._TOKEN_FILE) as f:
                    saved_tokens = json.load(f)
            except FileNotFoundError:
                with open(self._TOKEN_FILE, "w") as f:
                    saved_tokens = {"refresh_token": "", "access_token": ""}
                    json.dump(saved_tokens, f)
        else:  # reset json file when os env token updated
            with open(self._TOKEN_FILE, "w") as f:
                saved_tokens = {"refresh_token": "", "access_token": ""}
                json.dump(saved_tokens, f)
        saved_access_token = saved_tokens["access_token"]

        # decide which access token to use
        if saved_access_token == "":
            self.access_token = self.current_env_tokens["access_token"]
        else:
            self.access_token = saved_access_token

        self.headers["Authorization"] = "Bearer " + self.access_token
        self.room_id_list = [self._DEFAULT_ROOM_ID]
        self.webhook_events_cb: Dict[str, Dict[str, Callable]] = {}
        self.request_id_deque: deque = deque([], self._MAX_SAVED_REQUEST_ID)

    def update_tokens(self) -> None:
        """トークンの更新と保存

            jsonファイルに保存されているもしくは環境変数として設定されているrefresh tokenを用いて、
            refresh tokenとaccess tokenを更新、jsonファイルに保存します。

            access tokenが切れると自動で呼び出されるため、基本的に外部から使用することはありません。

        Raises
        ----------
        NoRefreshTokenError
            refresh tokenが設定されていない、もしくは間違っている場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/oauth/token/refresh

        API呼び出し回数
            最大2回
        """

        def _try_update_access_token(refresh_token):
            res_tokens = self.get_access_token(refresh_token)
            self.access_token = res_tokens.access_token
            refresh_token = res_tokens.refresh_token
            self.headers["Authorization"] = "Bearer " + self.access_token
            save_tokens = {
                "refresh_token": refresh_token,
                "access_token": self.access_token,
            }
            with open(self._TOKEN_FILE, "w") as f:
                json.dump(save_tokens, f)

        # load saved tokens
        with open(self._TOKEN_FILE, "r") as f:
            saved_tokens = json.load(f)
        refresh_token = saved_tokens["refresh_token"]

        # try with saved refresh token
        if refresh_token != "":
            try:
                _try_update_access_token(refresh_token)
            except UnauthorizedError:
                save_tokens = {"refresh_token": "", "access_token": ""}
                with open(self._TOKEN_FILE, "w") as f:
                    json.dump(save_tokens, f)
            else:
                return

        # try with current env refresh token
        refresh_token = self.current_env_tokens["refresh_token"]
        try:
            _try_update_access_token(refresh_token)
        except UnauthorizedError:
            pass
        else:
            return

        raise TokenError(
            "Please set new refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN'"
        )

    def _check_http_error(self, request: Callable, update_tokens: bool = True) -> dict:
        response = request()
        try:
            with _http_error_handler():
                response.raise_for_status()
        except UnauthorizedError:
            if not update_tokens:
                raise
        else:
            return response.json()

        self.update_tokens()
        response = request()
        with _http_error_handler():
            response.raise_for_status()
        return response.json()

    def _get(self, path: str, params: dict = {}) -> dict:
        request = partial(
            requests.get, self.endpoint_url + path, params=params, headers=self.headers
        )
        return self._check_http_error(request)

    def _post(
        self,
        path: str,
        data: str = "",
        files: Optional[dict] = None,
        content_type: Optional[str] = PostContentType.APPLICATION_JSON,
        update_tokens: bool = True,
    ) -> dict:
        self.headers["Content-Type"] = content_type
        request = partial(
            requests.post,
            self.endpoint_url + path,
            data=data,
            files=files,
            headers=self.headers,
        )
        return self._check_http_error(request, update_tokens=update_tokens)

    def _put(self, path: str, data: str = "{}") -> dict:
        request = partial(
            requests.put, self.endpoint_url + path, data=data, headers=self.headers
        )
        return self._check_http_error(request)

    def _delete(self, path: str) -> dict:
        request = partial(
            requests.delete, self.endpoint_url + path, headers=self.headers
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/oauth/token/refresh

        API呼び出し回数
            1回

        """

        payload = {"refresh_token": refresh_token}
        response = self._post(
            "/oauth/token/refresh", json.dumps(payload), update_tokens=False
        )
        return EmoTokens(**response)

    def get_account_info(
        self,
    ) -> Union[EmoAccountInfo, Coroutine[Any, Any, EmoAccountInfo]]:
        """アカウント情報の取得

        Returns
        -------
        account_info : EmoAccountInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/me

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self._get("/v1/me")
        return EmoAccountInfo(**response)

    def delete_account_info(
        self,
    ) -> Union[EmoAccountInfo, Coroutine[Any, Any, EmoAccountInfo]]:
        """アカウントの削除

            紐づくWebhook等の設定も全て削除されます。

        Returns
        -------
        account_info : EmoAccountInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているDELETEの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#delete-/v1/me

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self._delete("/v1/me")
        return EmoAccountInfo(**response)

    def get_rooms_list(self) -> Union[EmoRoomInfo, Coroutine[Any, Any, EmoRoomInfo]]:
        """ユーザが参加している部屋の一覧の取得

            取得可能な部屋は、「BOCCO emo Wi-Fiモデル」のものに限られます。

        Returns
        -------
        rooms_list : EmoRoomInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

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
            関数内部で行っているGETの処理が失敗した場合
            あるいは、ユーザーが参加している部屋が1つもなかった場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """
        result = self._get("/v1/rooms")
        try:
            room_number = len(result["rooms"])
        except KeyError:
            raise NoRoomError("Get no room id.")
        if room_number == 0:
            raise NoRoomError("Get no room id.")
        rooms_id = [result["rooms"][i]["uuid"] for i in range(room_number)]
        self.room_id_list = rooms_id + [self._DEFAULT_ROOM_ID]
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
    ) -> Union[EmoStampsInfo, Coroutine[Any, Any, EmoStampsInfo]]:
        """利用可能なスタンプ一覧の取得

        Returns
        -------
        stamps_info : EmoStampsInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/stamps

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self._get("/v1/stamps")
        return EmoStampsInfo(**response)

    def get_motions_list(
        self,
    ) -> Union[EmoMotionsInfo, Coroutine[Any, Any, EmoMotionsInfo]]:
        """利用可能なプリセットモーション一覧の取得

        Returns
        -------
        motions_info : EmoMotionsInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/motions

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self._get("/v1/motions")
        return EmoMotionsInfo(**response)

    def get_webhook_setting(
        self,
    ) -> Union[EmoWebhookInfo, Coroutine[Any, Any, EmoWebhookInfo]]:
        """現在設定されているWebhookの情報の取得

        Returns
        -------
        webhook_info : EmoWebhookInfo

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/webhook

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self._get("/v1/webhook")
        return EmoWebhookInfo(**response)

    def change_webhook_setting(
        self, webhook: WebHook
    ) -> Union[EmoWebhookInfo, Coroutine[Any, Any, EmoWebhookInfo]]:
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
            関数内部で行っているPUTの処理が失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"description": webhook.description, "url": webhook.url}
        response = self._put("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def register_webhook_event(
        self, events: List[str]
    ) -> Union[EmoWebhookInfo, Coroutine[Any, Any, EmoWebhookInfo]]:
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
            関数内部で行っているPUTの処理が失敗した場合。
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/webhook

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"description": webhook.description, "url": webhook.url}
        response = self._post("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def delete_webhook_setting(
        self,
    ) -> Union[EmoWebhookInfo, Coroutine[Any, Any, EmoWebhookInfo]]:
        """現在設定されているWebhookの情報の削除

        Returns
        -------
        webhook_info : EmoWebhookInfo
            削除したWebhookの情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているDELETEの処理が失敗した場合
            (BOCCO emoにWebhookの設定がされていない場合を含む)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#delete-/v1/webhook

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

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

        Raises
        ----------
        EmoPlatformError
            関数内部で呼んでいる :func:`get_rooms_id` が例外を出した場合
            あるいは、存在しない部屋idを引数 :attr:`room_id_list` に含めていた場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms

        API呼び出し回数
            :func:`get_rooms_id` を一度も実行していない状態で、
            引数 :attr:`room_id_list` に部屋idを指定して実行した場合: 1回 + 最大2回(access tokenが切れていた場合)

            上記以外の場合: 0回

        """

        def decorator(func):

            if event not in self.webhook_events_cb:
                self.webhook_events_cb[event] = {}

            if room_id_list != [self._DEFAULT_ROOM_ID]:
                if self.room_id_list == [self._DEFAULT_ROOM_ID]:
                    self.get_rooms_id()

            for room_id in room_id_list:
                if room_id in self.room_id_list:
                    self.webhook_events_cb[event][room_id] = func
                else:
                    raise NoRoomError(f"Try to register wrong room id: '{room_id}'")

        return decorator

    def start_webhook_event(self, host: str = "localhost", port: int = 8000) -> None:
        """BOCCO emoのWebhookのイベント通知の開始

            イベント通知時に、登録していた関数が呼び出されるようになります。

            使用する際は、以下の手順を踏んでください。

            1. ngrokなどを用いて、ローカルサーバーにForwardingするURLを発行

            2. :func:`create_webhook_setting` で、1で発行したURLをBOCCO emoに設定

            3. :func:`event` で通知したいeventとそれに対応するcallback関数を設定

            4. この関数を実行 (uvicornを使用して、ローカルサーバーを起動します。)

        Example
        -----
        この関数は、bloking処理になっている点に注意してください::

            import emo_platform

            client = emo_platform.Client()

            client.create_webhook_setting(emo_platform.WebHook("WEBHOOK URL"))

            @client.event("message.received")
            def test_event_callback(body):
                print(body)

            client.start_webhook_event()

        Parameters
        ----------
        host : str, default localhost
            Webhookの通知を受けるローカルサーバーのホスト名。

        port : int, default 8000
            Webhookの通知を受けるローカルサーバーのポート番号。

        Raises
        ----------
        EmoPlatformError
            関数内部で呼んでいる :func:`register_webhook_event` が例外を出した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self.register_webhook_event(list(self.webhook_events_cb.keys()))
        secret_key = response.secret

        self.app = FastAPI()

        @self.app.post("/")
        def emo_callback(
            request: Request, body: EmoWebhookBody, background_tasks: BackgroundTasks
        ):
            if request.headers.get("x-platform-api-secret") == secret_key:
                if body.request_id not in self.request_id_deque:
                    try:
                        event_cb = self.webhook_events_cb[body.event]
                    except KeyError:
                        return "fail. no callback associated with the event.", 500
                    room_id = body.uuid
                    if room_id in event_cb:
                        cb_func = event_cb[room_id]
                    elif self._DEFAULT_ROOM_ID in event_cb:
                        cb_func = event_cb[self._DEFAULT_ROOM_ID]
                    else:
                        return "fail. no callback associated with the room.", 500
                    background_tasks.add_task(cb_func, body)
                    self.request_id_deque.append(body.request_id)
                    return "success", 200

        uvicorn.run(self.app, host=host, port=port)


class Room:
    """部屋固有の各種apiを呼び出すclient

    Parameters
    ----------
    base_client : Client
        このclientを作成しているclient。

    room_id : str
        部屋のuuid。

    """

    def __init__(self, base_client: Client, room_id: str):
        self.base_client = base_client
        self.room_id = room_id

    def get_msgs(
        self, ts: int = None
    ) -> Union[EmoMsgsInfo, Coroutine[Any, Any, EmoMsgsInfo]]:
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
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/messages

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        params = {"before": ts} if ts else {}
        response = self.base_client._get(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )
        return EmoMsgsInfo(**response)

    def get_sensors_list(
        self,
    ) -> Union[EmoSensorsInfo, Coroutine[Any, Any, EmoSensorsInfo]]:
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
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/sensors

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self.base_client._get("/v1/rooms/" + self.room_id + "/sensors")
        return EmoSensorsInfo(**response)

    def get_sensor_values(
        self, sensor_id: str
    ) -> Union[EmoRoomSensorInfo, Coroutine[Any, Any, EmoRoomSensorInfo]]:
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
            関数内部で行っているGETの処理が失敗した場合。
            (部屋センサ以外のBOCCOセンサ / 紐づいていない部屋センサ、のidを指定した場合も含みます)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/sensors/-sensor_uuid-/values

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self.base_client._get(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )
        return EmoRoomSensorInfo(**response)

    def send_audio_msg(
        self, audio_data_path: str
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/audio

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        with open(audio_data_path, "rb") as audio_data:
            files = {"audio": audio_data}
            response = self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    def send_image(
        self, image_data_path: str
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/image

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        with open(image_data_path, "rb") as image_data:
            files = {"image": image_data}
            response = self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/image",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    def send_msg(
        self, msg: str
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/text

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"text": msg}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_stamp(
        self, stamp_id: str, msg: Optional[str] = None
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/messages/stamp

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_original_motion(
        self, motion_data: Union[str, dict]
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
        """独自定義した、オリジナルのモーションをBOCCO emoに送信

            詳しくは、
            `こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions>`_
            を参照してください。

        Parameters
        ----------
        file_path : str or dict
            モーションファイルを置いている絶対パス。

            あるいは、モーションを記述した辞書オブジェクト。

        Returns
        -------
        response : EmoMessageInfo
            モーション送信時の情報。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。
            (モーションのデータ形式が誤っている場合も含みます)

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        if type(motion_data) == str:
            with open(motion_data) as f:
                payload = json.load(f)
        else:
            payload = motion_data
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def change_led_color(
        self, color: Color
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions/led_color

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def move_to(
        self, head: Head
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions/move_to

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_motion(
        self, motion_id: str
    ) -> Union[EmoMessageInfo, Coroutine[Any, Any, EmoMessageInfo]]:
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
            関数内部で行っているPOSTの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions/preset

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        payload = {"uuid": motion_id}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def get_emo_settings(
        self,
    ) -> Union[EmoSettingsInfo, Coroutine[Any, Any, EmoSettingsInfo]]:
        """現在のBOCCO emoの設定値を取得

        Returns
        -------
        settings : EmoSettingsInfo
            取得した設定値。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        Note
        ----
        呼び出しているAPI
            https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/emo/settings

        API呼び出し回数
            1回 + 最大2回(access tokenが切れていた場合)

        """

        response = self.base_client._get("/v1/rooms/" + self.room_id + "/emo/settings")
        return EmoSettingsInfo(**response)
