import json
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, List, Optional

import requests
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel

from emo_platform.exceptions import (
    NoRefreshTokenError,
    NoRoomError,
    UnauthorizedError,
    http_error_handler,
)
from emo_platform.models import Color, Head, WebHook

EMO_PLATFORM_PATH = os.path.abspath(os.path.dirname(__file__))


class EmoWebhook(BaseModel):
    """BOCCO emoからのWebhook通知のデータフォーマット"""
    request_id: str
    uuid: str
    serial_number: str
    nickname: str
    timestamp: int
    event: str
    data: dict
    receiver: str


class PostContentType:
    """POSTするデータの種類"""
    APPLICATION_JSON = "application/json"
    MULTIPART_FORMDATA = None


class Client:
    """
    各種apiを呼び出すclient。

    Parameters
    ----------
    endpoint_url : str, default https://platform-api.bocco.me
        BOCCO emo platform apiにアクセスするためのendpoint。

    Raises
    ----------
    NoRefreshTokenError
        refresh tokenが設定されていない、もしくは間違っている場合。

    Note
    ----
    保存されているaccess tokenの期限が切れていた場合
        保存されているrefresh tokenをもとに自動的に更新される。その際にAPI呼び出しが1回行われる。

    """
    BASE_URL = "https://platform-api.bocco.me"
    TOKEN_FILE = f"{EMO_PLATFORM_PATH}/tokens/emo-platform-api.json"
    DEFAULT_ROOM_ID = ""
    MAX_SAVED_REQUEST_ID = 10

    def __init__(self, endpoint_url: str = BASE_URL):
        self.endpoint_url = endpoint_url
        self.headers = {
            "accept": "*/*",
            "Content-Type": PostContentType.APPLICATION_JSON,
        }
        with open(self.TOKEN_FILE) as f:
            tokens = json.load(f)
        access_token = tokens["access_token"]

        if access_token == "":
            try:
                self.access_token = os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"]
            except KeyError:
                self.update_tokens()
        else:
            self.access_token = access_token

        self.headers["Authorization"] = "Bearer " + self.access_token
        self.room_id_list = [self.DEFAULT_ROOM_ID]
        self.webhook_events_cb = {}
        self.request_id_deque = deque([], self.MAX_SAVED_REQUEST_ID)
        self.webhook_cb_executor = ThreadPoolExecutor()

    def update_tokens(self) -> None:
        """
        refresh tokenを用いて、refresh tokenとaccess tokenを取得して、jsonファイルに保存する。

        Raises
        ----------
        NoRefreshTokenError
            refresh tokenが設定されていない、もしくは間違っている場合。

        """
        with open(self.TOKEN_FILE, "r") as f:
            tokens = json.load(f)
        refresh_token = tokens["refresh_token"]

        if refresh_token != "":
            try:
                refresh_token, self.access_token = self.get_access_token(refresh_token)
                self.headers["Authorization"] = "Bearer " + self.access_token
                tokens["refresh_token"] = refresh_token
                tokens["access_token"] = self.access_token
                with open(self.TOKEN_FILE, "w") as f:
                    json.dump(tokens, f)
            except UnauthorizedError:
                tokens["refresh_token"] = ""
                tokens["access_token"] = ""
                with open(self.TOKEN_FILE, "w") as f:
                    json.dump(tokens, f)
                refresh_token = ""

        if refresh_token == "":
            try:
                refresh_token = os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"]
            except KeyError:
                raise NoRefreshTokenError(
                    "Please set refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN'"
                )

            try:
                refresh_token, self.access_token = self.get_access_token(refresh_token)
                self.headers["Authorization"] = "Bearer " + self.access_token
                tokens["refresh_token"] = refresh_token
                tokens["access_token"] = self.access_token
                with open(self.TOKEN_FILE, "w") as f:
                    json.dump(tokens, f)
            except UnauthorizedError:
                raise NoRefreshTokenError(
                    "Please set new refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN'"
                )

    def _check_http_error(self, request: Callable, update_tokens: bool = True) -> dict:
        response = request()
        try:
            with http_error_handler():
                response.raise_for_status()
        except UnauthorizedError:
            if not update_tokens:
                raise UnauthorizedError("Unauthorized error while getting access_token")
            self.update_tokens()
            response = request()
            with http_error_handler():
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
        data: dict = {},
        files: Optional[dict] = None,
        content_type: PostContentType = PostContentType.APPLICATION_JSON,
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

    def _put(self, path: str, data: dict = {}) -> dict:
        request = partial(
            requests.put, self.endpoint_url + path, data=data, headers=self.headers
        )
        return self._check_http_error(request)

    def _delete(self, path: str) -> dict:
        request = partial(
            requests.delete, self.endpoint_url + path, headers=self.headers
        )
        return self._check_http_error(request)

    def get_access_token(self, refresh_token: str) -> tuple:
        """
        refresh_tokenを用いて、refresh tokenとaccess tokenを取得する。

        Parameters
        ----------
        refresh_token : str
            refresh tokenとaccess tokenを取得するのに用いるrefresh token。

        Returns
        -------
        refresh_token, access_token : tuple
            取得したrefresh tokenとaccess token。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"refresh_token": refresh_token}
        result = self._post(
            "/oauth/token/refresh", json.dumps(payload), update_tokens=False
        )
        return result["refresh_token"], result["access_token"]

    def get_account_info(self) -> dict:
        """
        アカウント情報を取得する。

        Returns
        -------
        account_info : dict
            取得したアカウント情報。
            {
                name:          str,
                email:         str,
                profile_image: str,
                uuid:          str,
                plan:          str
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self._get("/v1/me")

    def delete_account_info(self) -> dict:
        """
        アカウントを削除する。
        アカウントを削除すると、紐づくWebhook等の設定も全て削除される。

        Returns
        -------
        account_info : dict
            削除したアカウント情報。
            {
                name:          str,
                email:         str,
                profile_image: str,
                uuid:          str,
                plan:          str
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているDELETEの処理が失敗した場合。

        """
        return self._delete("/v1/me")

    def get_rooms_list(self) -> dict:
        """
        ユーザが参加している部屋の一覧を取得する。
        取得可能な部屋は、「BOCCO emo Wi-Fiモデル」のものに限られる。

        Returns
        -------
        rooms_list : dict
            取得した部屋一覧情報。
            {
                listing: {
                    offset: int,
                    limit:  int,
                    total:  int,
                }
                rooms: [{
                    uuid:      str,
                    name:      str,
                    room_type: str,
                    room_members: [{
                        uuid:          str,
                        user_type:     str,
                        nickname:      str,
                        profile_image: str,
                    }]
                }]
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self._get("/v1/rooms")

    def get_rooms_id(self) -> List[str]:
        """
        ユーザーが参加している全ての部屋のidを取得する。

        Returns
        -------
        rooms_id : List[str]
            取得した部屋のid。

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合
            あるいは、ユーザーが参加している部屋が1つもなかった場合。

        """
        result = self._get("/v1/rooms")
        try:
            room_number = len(result["rooms"])
        except KeyError:
            raise NoRoomError("Get no room id.")
        rooms_id = [result["rooms"][i]["uuid"] for i in range(room_number)]
        self.room_id_list = rooms_id + [self.DEFAULT_ROOM_ID]
        return rooms_id

    def create_room_client(self, room_id: str):
        """
        部屋固有の各種apiを呼び出すclientを作成する。

        Parameters
        ----------
        room_id : str
            部屋のid。

        Returns
        -------
        room_client : Room
            部屋のclient。

        """
        return Room(self, room_id)

    def get_stamps_list(self) -> dict:
        """
        利用可能なスタンプ一覧を取得する。

        Returns
        -------
        stamps_info : dict
            取得したスタンプ一覧情報。
            {
                listing: {
                    offset: int,
                    limit:  int,
                    total:  int,
                }
                stamps: [{
                    uuid:    str,
                    name:    str,
                    summary: str,
                    image:   str
                }]
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self._get("/v1/stamps")

    def get_motions_list(self) -> dict:
        """
        利用可能なプリセットモーション一覧を取得する。

        Returns
        -------
        stamps_info : dict
            取得したプリセットモーション一覧情報。
            {
                listing: {
                    offset: int,
                    limit:  int,
                    total:  int,
                }
                motions: [{
                    name:    str,
                    uuid:    str,
                    preview: str,
                }]
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self._get("/v1/motions")

    def get_webhook_setting(self) -> dict:
        """
        現在設定されているWebhookの情報を取得する。

        Returns
        -------
        webhook_info : dict
            現在のWebhookの設定。
            {
                description: str,
                events:      List[str],
                status:      str,
                secret:      str,
                url:         str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合
            あるいは、BOCCO emoにWebhookの設定がされていない場合。

        """
        return self._get("/v1/webhook")

    def change_webhook_setting(self, webhook: WebHook) -> dict:
        """
        Webhookの設定を変更する。

        Parameters
        ----------
        webhook : emo_platform.WebHook
            適用するWebhookの設定。

        Returns
        -------
        webhook_info : dict
            変更後のWebhookの設定。
            {
                description: str,
                events:      List[str],
                status:      str,
                secret:      str,
                url:         str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPUTの処理が失敗した場合
            あるいは、BOCCO emoにWebhookの設定がされていない場合。

        """
        payload = {"description": webhook.description, "url": webhook.url}
        return self._put("/v1/webhook", json.dumps(payload))

    def register_webhook_event(self, events: List[str]) -> dict:
        """
        Webhook通知するイベントを指定する。

        Parameters
        ----------
        events : List[str]
            指定するWebhook event。
            eventの種類は下記から確認できる。
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        Returns
        -------
        webhook_info : dict
            設定したWebhookの情報。
            {
                description: str,
                events:      List[str],
                status:      str,
                secret:      str,
                url:         str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPUTの処理が失敗した場合
            あるいは、BOCCO emoにWebhookの設定がされていない場合。

        """
        payload = {"events": events}
        return self._put("/v1/webhook/events", json.dumps(payload))

    def create_webhook_setting(self, webhook: WebHook) -> dict:
        """
        Webhookの設定を作成する。

        Parameters
        ----------
        webhook : emo_platform.WebHook
            作成するWebhookの設定。

        Returns
        -------
        webhook_info : dict
            作成したWebhookの設定。
            {
                description: str,
                events:      List[str],
                status:      str,
                secret:      str,
                url:         str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"description": webhook.description, "url": webhook.url}
        return self._post("/v1/webhook", json.dumps(payload))

    def delete_webhook_setting(self) -> dict:
        """
        現在設定されているWebhookの情報を削除する。

        Returns
        -------
        webhook_info : dict
            削除したWebhookの情報。
            {
                description: str,
                events:      list,
                status:      str,
                secret:      str,
                url:         str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているDELETEの処理が失敗した場合
            あるいは、BOCCO emoにWebhookの設定がされていない場合。

        """
        return self._delete("/v1/webhook")

    def event(
        self, event: str, room_id_list: List[str] = [DEFAULT_ROOM_ID]
    ) -> Callable:
        """
        Webhookの指定のeventが通知されたときに呼び出す関数を登録する。

        Usage
        -----
            client = emo_platform.Client()
            @client.event("message.received")
            def test_event_callback(body):
                print(body)

        Parameters
        ----------
        event : str
            指定するWebhook event。
            eventの種類は下記から確認できる。
            https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events

        room_id_list : List[str], default [""]
            指定したWebhook eventの通知を監視する部屋を指定できる。
            引数なしだと、全ての部屋を監視する。

        Raises
        ----------
        EmoPlatformError
            関数内部呼んでいるget_rooms_id()が例外を出した場合
            あるいは、存在しない部屋を引数:room_id_listに含めていた場合。

        """
        def decorator(func):

            if event not in self.webhook_events_cb:
                self.webhook_events_cb[event] = {}

            if self.room_id_list == [self.DEFAULT_ROOM_ID]:
                self.get_rooms_id()

            for room_id in room_id_list:
                if room_id in self.room_id_list:
                    self.webhook_events_cb[event][room_id] = func
                else:
                    raise NoRoomError(f"Try to register wrong room id: '{room_id}'")

        return decorator

    def start_webhook_event(self, host: str = "localhost", port: int = 8000) -> None:
        """
        BOCCO emoのWebhookのイベント通知を開始し、通知時に登録した関数が呼び出されるようにする。

        Usage
        -----
        bloking処理になっているため、以下の例のようにスレッドを立てて用いる。

            client = emo_platform.Client()
            @client.event("message.received")
            def test_event_callback(body):
                print(body)
            thread = Thread(target=client.start_webhook_event)
            thread.start()

            # main処理
            main()

        Parameters
        ----------
        host : str, default localhost
            Webhookの通知を受けるローカルサーバーのホスト名。

        port : int, default 8000
            Webhookの通知を受けるローカルサーバーのポート番号。

        Raises
        ----------
        EmoPlatformError
            関数内部で呼んでいるregister_webhook_event()が例外を出した場合。

        """
        response = self.register_webhook_event(list(self.webhook_events_cb.keys()))
        secret_key = response["secret"]

        self.app = FastAPI()

        @self.app.post("/")
        def emo_callback(request: Request, body: EmoWebhook):
            if request.headers.get("x-platform-api-secret") == secret_key:
                if body.request_id not in self.request_id_deque:
                    try:
                        event_cb = self.webhook_events_cb[body.event]
                    except KeyError:
                        return "fail. no callback associated with the event.", 500
                    room_id = body.uuid
                    if room_id in event_cb:
                        cb_func = event_cb[room_id]
                    elif self.DEFAULT_ROOM_ID in event_cb:
                        cb_func = event_cb[self.DEFAULT_ROOM_ID]
                    else:
                        return "fail. no callback associated with the room.", 500
                    self.webhook_cb_executor.submit(cb_func, body)
                    self.request_id_deque.append(body.request_id)
                    return "success", 200

        uvicorn.run(self.app, host=host, port=port)


class Room:
    """
    部屋固有の各種apiを呼び出すclient。

    Parameters
    ----------
    base_client : emo_platform.Client
        このclientを作成しているclient。

    room_id : str
        部屋のuuid。

    """
    def __init__(self, base_client: Client, room_id: str):
        self.base_client = base_client
        self.room_id = room_id

    def get_msgs(self, ts: Optional[int] = None) -> dict:
        """
        部屋に投稿されたメッセージを取得する。

        Parameters
        ----------
        ts : int or None
            指定した場合は、その時刻以前のメッセージを取得できる。
            指定の仕方：2021/07/01 12:30:45以前なら、20210701123045000

        Returns
        -------
        response : dict
            投稿されたメッセージの情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        params = {"before": ts} if ts else {}
        return self.base_client._get(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )

    def get_sensors_list(self) -> dict:
        """
        BOCCO emoとペアリングされているセンサの一覧を取得する。

        Notes
        -----
        センサの種別
            sensor_type	センサの種別
            movement	振動センサ
            human	人感センサ
            lock	鍵センサ
            room	部屋センサ

        Returns
        -------
        sensors_info : dict
            取得した設定値。
            {
                sensors: [{
                    uuid:            str,
                    sensor_type:     str,
                    nickname:        str,
                    signal_strength: int,
                    battery:         int,
                }]
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self.base_client._get("/v1/rooms/" + self.room_id + "/sensors")

    def get_sensor_values(self, sensor_id: str) -> dict:
        """
        部屋センサの送信値を取得する。

        Parameters
        ----------
        sensor_id : str
            部屋センサのuuid。
            各部屋センサのuuidは、センサ一覧取得(get_sensors_list)で確認できる。

        Returns
        -------
        response : dict
            部屋センサの送信値の情報。
            {
                sensor_type: str,
                uuid:        str,
                nickname:    str,
                events: [{
                    temperature: int or float,
                    humidity:    int or float,
                    illuminance: int or float,
                }]
            }
        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self.base_client._get(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )

    def send_audio_msg(self, audio_data_path: str) -> dict:
        """
        音声ファイルを部屋に投稿する。

        Note
        ----
        送信できるファイルには下記の制限がある。
            フォーマット:    MP3, M4A
            ファイルサイズ:  1MB

        Parameters
        ----------
        audio_data_path : str
            投稿する音声ファイルの絶対パス。

        Returns
        -------
        response : dict
            音声ファイル投稿時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        with open(audio_data_path, "rb") as audio_data:
            files = {"audio": audio_data}
            return self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )

    def send_image(self, image_data_path: str) -> dict:
        """
        画像ファイルを部屋に投稿する。

        Note
        ----
        送信できるファイルには下記の制限がある。
            フォーマット:    JPG, PNG
            ファイルサイズ:  1MB

        Parameters
        ----------
        image_data_path : str
            投稿する画像ファイルの絶対パス。

        Returns
        -------
        response : dict
            画像投稿時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        with open(image_data_path, "rb") as image_data:
            files = {"image": image_data}
            return self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/image",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )

    def send_msg(self, msg: str) -> dict:
        """
        テキストメッセージを部屋に投稿する。

        Parameters
        ----------
        msg : str
            投稿するメッセージ。

        Returns
        -------
        response : dict
            メッセージ投稿時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"text": msg}
        return self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )

    def send_stamp(self, stamp_id: str, msg: Optional[str] = None) -> dict:
        """
        スタンプを部屋に投稿する。

        Parameters
        ----------
        stamp_id : str
            スタンプのuuid。
            各スタンプのuuidは、スタンプ一覧取得(get_stamps_list)で確認できる。

        msg : Optional[str], default None
            スタンプ投稿時に、BOCCO emoが行うモーション再生と共に発話されるメッセージ。
            Noneの場合は、発話なしでモーションが再生される。

        Returns
        -------
        response : dict
            スタンプモーション送信時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        return self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )

    def send_original_motion(self, file_path: str) -> dict:
        """
        独自定義した、オリジナルのモーションをBOCCO emoに送信する。
        詳しくは、以下を参照。
        https://platform-api.bocco.me/dashboard/api-docs#post-/v1/rooms/-room_uuid-/motions

        Parameters
        ----------
        file_path : str
            モーションファイルを置いている絶対パス。

        Returns
        -------
        response : dict
            モーション送信時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        with open(file_path) as f:
            payload = json.load(f)
            return self.base_client._post(
                "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
            )

    def change_led_color(self, color: Color) -> dict:
        """
        3秒間のみ、ほっぺたの色を指定した色に変更するモーションをBOCCO emoに送信する。

        Parameters
        ----------
        color : emo_platform.Color
            送信するほっぺたの色。

        Returns
        -------
        response : dict
            モーション送信時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        return self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )

    def move_to(self, head: Head) -> dict:
        """
        首の角度を変更するモーションをBOCCO emoに送信する。

        Parameters
        ----------
        head : emo_platform.Head
            送信する首の角度。

        Returns
        -------
        response : dict
            モーション送信時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }
        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        return self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )

    def send_motion(self, motion_id: str) -> dict:
        """
        プリセットモーションをBOCCO emoに送信する。

        Parameters
        ----------
        motion_id : str
            プリセットモーションのuuid
            各プリセットモーションのuuidは、モーション一覧取得(get_motions_list)で確認できる。

        Returns
        -------
        response : dict
            モーション送信時の情報。
            {
                sequence:  int,
                unique_id: str,
                user: {
                    uuid:          str,
                    user_type:     str,
                    nickname:      str,
                    profile_image: str,
                }
                message: {
                    ja: str,
                }
                media:     str,
                audio_url: str,
                image_url: str,
                lang:      str,
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているPOSTの処理が失敗した場合。

        """
        payload = {"uuid": motion_id}
        return self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )

    def get_emo_settings(self) -> dict:
        """
        現在のBOCCO emoの設定値を取得する。

        Returns
        -------
        settings : dict
            取得した設定値。
            {
                nickname:      str,
                wakeword:      str,
                volume:        int,
                voice_pitch:   int,
                voice_speed:   int,
                lang:          str,
                serial_number: str,
                timezone:      str,
                zip_code:      str
            }

        Raises
        ----------
        EmoPlatformError
            関数内部で行っているGETの処理が失敗した場合。

        """
        return self.base_client._get("/v1/rooms/" + self.room_id + "/emo/settings")
