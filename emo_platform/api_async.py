import asyncio
import json
from dataclasses import asdict
from functools import partial
from typing import Callable, List, NoReturn, Optional, Union

import aiohttp
import uvicorn  # type: ignore
from fastapi import BackgroundTasks, FastAPI, Request

from emo_platform.api import Client, PostContentType
from emo_platform.exceptions import (
    TokenError,
    UnauthorizedError,
    UnavailableError,
    _aiohttp_error_handler,
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
    EmoPaymentInfo,
    EmoPaymentsInfo,
    EmoRoomInfo,
    EmoRoomSensorInfo,
    EmoSensorsInfo,
    EmoSettingsInfo,
    EmoStampsInfo,
    EmoTokens,
    EmoWebhookBody,
    EmoWebhookInfo,
)


class AsyncClient:
    _DEFAULT_ROOM_ID = Client._DEFAULT_ROOM_ID
    _MAX_SAVED_REQUEST_ID = Client._MAX_SAVED_REQUEST_ID
    PLAN = "Personal"

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        tokens: Optional[Tokens] = None,
        token_file_path: Optional[str] = None,
    ):
        self._client = Client(endpoint_url, tokens, token_file_path)

    async def update_tokens(self) -> None:

        try:
            res_tokens = await self.get_access_token(
                self._client.tm.tokens.refresh_token
            )
        except UnauthorizedError as e:
            raise TokenError(
                "Please set new refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN'"
            ) from e
        else:
            self._client.tm.tokens.access_token = res_tokens.access_token
            self._client.tm.tokens.refresh_token = res_tokens.refresh_token
            self._client.headers["Authorization"] = (
                "Bearer " + self._client.tm.tokens.access_token
            )
            self._client.tm.save_tokens()
            return

    async def _check_http_error(
        self, request: Callable, update_tokens: bool = True
    ) -> dict:
        async with request() as response:
            try:
                response_msg = await response.text()
                with _aiohttp_error_handler(response_msg):
                    response.raise_for_status()
            except UnauthorizedError:
                if not update_tokens:
                    raise
            else:
                return await response.json()

        await self.update_tokens()
        async with request() as response:
            response_msg = await response.text()
            with _aiohttp_error_handler(response_msg):
                response.raise_for_status()
            return await response.json()

    async def _get(self, path: str, params: dict = {}) -> dict:
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.get,
                self._client.endpoint_url + path,
                params=params,
                headers=self._client.headers,
            )
            return await self._check_http_error(request)

    async def _post(
        self,
        path: str,
        data: Union[str, aiohttp.FormData] = "{}",
        files: Optional[dict] = None,
        content_type: Optional[str] = PostContentType.APPLICATION_JSON,
        update_tokens: bool = True,
    ) -> dict:
        if content_type is None:
            if "Content-Type" in self._client.headers:
                self._client.headers.pop("Content-Type")
        else:
            self._client.headers["Content-Type"] = content_type
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.post,
                self._client.endpoint_url + path,
                data=data,
                headers=self._client.headers,
            )
            return await self._check_http_error(request, update_tokens=update_tokens)

    async def _put(self, path: str, data: str = "{}") -> dict:
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.put,
                self._client.endpoint_url + path,
                data=data,
                headers=self._client.headers,
            )
            return await self._check_http_error(request)

    async def _delete(self, path: str) -> dict:
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.delete,
                self._client.endpoint_url + path,
                headers=self._client.headers,
            )
            return await self._check_http_error(request)

    async def get_access_token(self, refresh_token: str) -> EmoTokens:
        payload = {"refresh_token": refresh_token}
        response = await self._post(
            "/oauth/token/refresh", json.dumps(payload), update_tokens=False
        )
        return EmoTokens(**response)

    async def _get_account_info(self) -> dict:
        return await self._get("/v1/me")

    async def get_account_info(self) -> EmoAccountInfo:
        response = await self._get_account_info()
        return EmoAccountInfo(**response)

    async def delete_account_info(self) -> EmoAccountInfo:
        response = await self._delete("/v1/me")
        return EmoAccountInfo(**response)

    async def get_rooms_list(self) -> EmoRoomInfo:
        response = await self._get("/v1/rooms")
        return EmoRoomInfo(**response)

    async def get_rooms_id(self) -> List[str]:
        rooms_info = await self.get_rooms_list()
        return self._client._get_rooms_id(rooms_info)

    def create_room_client(self, room_id: str):
        return AsyncRoom(self, room_id)

    async def get_stamps_list(self) -> EmoStampsInfo:
        response = await self._get("/v1/stamps")
        return EmoStampsInfo(**response)

    async def get_motions_list(self) -> EmoMotionsInfo:
        response = await self._get("/v1/motions")
        return EmoMotionsInfo(**response)

    async def get_webhook_setting(self) -> EmoWebhookInfo:
        response = await self._get("/v1/webhook")
        return EmoWebhookInfo(**response)

    async def change_webhook_setting(self, webhook: WebHook) -> EmoWebhookInfo:
        payload = {"description": webhook.description, "url": webhook.url}
        response = await self._put("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    async def register_webhook_event(self, events: List[str]) -> EmoWebhookInfo:
        payload = {"events": events}
        response = await self._put("/v1/webhook/events", json.dumps(payload))
        return EmoWebhookInfo(**response)

    async def create_webhook_setting(self, webhook: WebHook) -> EmoWebhookInfo:
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
            1回 + 1回(access tokenが切れていた場合)

        """

        payload = {"description": webhook.description, "url": webhook.url}
        response = await self._post("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    async def delete_webhook_setting(self) -> EmoWebhookInfo:
        response = await self._delete("/v1/webhook")
        return EmoWebhookInfo(**response)

    def event(
        self, event: str, room_id_list: List[str] = [_DEFAULT_ROOM_ID]
    ) -> Callable:
        """Webhookの指定のeventが通知されたときに呼び出す関数の登録

        Example
        -----
        呼び出したい関数にdecorateして登録します::

            import emo_platform

            client = emo_platform.AsyncClient()

            @client.event("message.received")
            async def test_event_callback(body):
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

            if event not in self._client.webhook_events_cb:
                self._client.webhook_events_cb[event] = {}

            for room_id in room_id_list:
                self._client.webhook_events_cb[event][room_id] = func

        return decorator

    async def start_webhook_event(
        self, host: str = "localhost", port: int = 8000, tasks: List[asyncio.Task] = []
    ) -> None:
        """BOCCO emoのWebhookのイベント通知の開始

            イベント通知時に、登録していた関数が呼び出されるようになります。

            使用する際は、以下の手順を踏んでください。

            1. ngrokなどを用いて、ローカルサーバーにForwardingするURLを発行

            2. :func:`create_webhook_setting` で、1で発行したURLをBOCCO emoに設定

            3. :func:`event` で通知したいeventとそれに対応するcallback関数を設定

            4. この関数を実行 (uvicornを使用して、ローカルサーバーを起動します。)

        Example
        -----
        webhook通知が来たらそのデータをqueueに渡し、:func:`print_queue` で表示する例です::

            import emo_platform

            client = emo_platform.AsyncClient()

            client.create_webhook_setting(emo_platform.WebHook("WEBHOOK URL"))

            async def print_queue(queue):
                while True:
                    item = await queue.get()
                    print("body:", item)
                    print("data:", item.data)

            async def main():
                queue = asyncio.Queue()

                @client.event("message.received")
                async def message_callback(body):
                    await queue.put(body)

                # Create task you want to execute in parallel
                task_queue = asyncio.create_task(print_queue(queue))

                # Await start_webhook_event last.
                # Give task list to be executed in parallel as the argument.
                await client.start_webhook_event(port=8000, tasks=[task_queue])

            if __name__ == "__main__":
                asyncio.run(main())


        Parameters
        ----------
        host : str, default localhost
            Webhookの通知を受けるローカルサーバーのホスト名。

        port : int, default 8000
            Webhookの通知を受けるローカルサーバーのポート番号。

        tasks : List[asyncio.Task], default []
            並列で実行したいタスクオブジェクトのリスト。

            サーバー終了時にキャンセルされます。

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

        response = await self.register_webhook_event(
            list(self._client.webhook_events_cb.keys())
        )
        secret_key = response.secret

        self.app = FastAPI()

        @self.app.post("/")
        async def emo_callback(
            request: Request, body: EmoWebhookBody, background_tasks: BackgroundTasks
        ):
            if request.headers.get("x-platform-api-secret") == secret_key:
                if body.request_id not in self._client.request_id_deque:
                    try:
                        event_cb = self._client.webhook_events_cb[body.event]
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
                    self._client.request_id_deque.append(body.request_id)
                    return "success", 200

        loop = asyncio.get_event_loop()
        config = uvicorn.Config(
            app=self.app, host=host, port=port, loop=loop, lifespan="off"
        )
        self.server = uvicorn.Server(config)
        await self.server.serve()
        for task in tasks:
            task.cancel()

    def stop_webhook_event(self):
        self.server.should_exit = True


class BizAsyncClient(AsyncClient):
    PLAN = "Business"

    def __init__(
        self,
        x_channel_user: str,
        endpoint_url: Optional[str] = None,
        tokens: Optional[Tokens] = None,
        token_file_path: Optional[str] = None,
    ):
        super().__init__(
            endpoint_url=endpoint_url, tokens=tokens, token_file_path=token_file_path
        )
        self._client.headers["X-Channel-User"] = x_channel_user

    async def get_account_info(self) -> EmoBizAccountInfo:  # type: ignore[override]
        response = await self._get_account_info()
        return EmoBizAccountInfo(**response)

    async def delete_account_info(self) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def change_account_info(self, acount: AccountInfo) -> EmoBizAccountInfo:
        payload = asdict(acount)
        response = await self._put("/v1/me", json.dumps(payload))
        return EmoBizAccountInfo(**response)

    async def get_broadcast_msgs_list(self) -> EmoBroadcastInfoList:
        response = await self._get("/v1/broadcast_messages")
        return EmoBroadcastInfoList(**response)

    async def get_broadcast_msg_details(self, message_id: int) -> EmoBroadcastInfo:
        response = await self._get("/v1/broadcast_messages/" + str(message_id))
        return EmoBroadcastInfo(**response)

    async def create_broadcast_msg(self, message: BroadcastMsg) -> EmoBroadcastMessage:
        payload = asdict(message)
        if message.immediate:
            payload.pop("executed_at")
        response = await self._post("/v1/broadcast_messages", json.dumps(payload))
        return EmoBroadcastMessage(**response)

    async def get_payments_info(self) -> EmoPaymentsInfo:
        response = await self._get("/v1/payments")
        return EmoPaymentsInfo(**response)

    async def get_payment_info_detail(self, payment_id: int) -> EmoPaymentInfo:
        response = await self._get("/v1/payments/" + str(payment_id))
        return EmoPaymentInfo(**response)


class BizBasicAsyncClient(BizAsyncClient):
    PLAN = "Business Basic"

    def create_room_client(self, room_id: str):
        return BizBasicAsyncRoom(self, room_id)

    async def get_motions_list(self) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def get_webhook_setting(
        self,
    ) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def change_webhook_setting(self, webhook: WebHook) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def register_webhook_event(self, events: List[str]) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def create_webhook_setting(self, webhook: WebHook) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def delete_webhook_setting(
        self,
    ) -> NoReturn:
        raise UnavailableError(self.PLAN)

    def event(
        self, event: str, room_id_list: List[str] = [Client._DEFAULT_ROOM_ID]
    ) -> NoReturn:
        raise UnavailableError(self.PLAN)

    async def start_webhook_event(
        self, host: str = "localhost", port: int = 8000, tasks: List[asyncio.Task] = []
    ) -> NoReturn:
        raise UnavailableError(self.PLAN)


class BizAdvancedAsyncClient(BizAsyncClient):
    PLAN = "Business Advanced"

    def create_room_client(self, room_id: str):
        return BizAdvancedAsyncRoom(self, room_id)


class AsyncRoom:
    def __init__(self, base_client: AsyncClient, room_id: str):
        self.base_client = base_client
        self.room_id = room_id

    async def get_msgs(self, ts: int = None) -> EmoMsgsInfo:
        params = {"before": ts} if ts else {}
        response = await self.base_client._get(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )
        return EmoMsgsInfo(**response)

    async def get_sensors_list(self) -> EmoSensorsInfo:
        response = await self.base_client._get("/v1/rooms/" + self.room_id + "/sensors")
        return EmoSensorsInfo(**response)

    async def get_sensor_values(self, sensor_id: str) -> EmoRoomSensorInfo:
        response = await self.base_client._get(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )
        return EmoRoomSensorInfo(**response)

    async def send_audio_msg(self, audio_data_path: str) -> EmoMessageInfo:
        with open(audio_data_path, "rb") as audio_data:
            data = aiohttp.FormData()
            data.add_field("audio", audio_data, content_type="multipart/form-data")
            response = await self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                data=data,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    async def send_image(self, image_data_path: str) -> EmoMessageInfo:
        with open(image_data_path, "rb") as image_data:
            data = aiohttp.FormData()
            data.add_field("image", image_data, content_type="multipart/form-data")
            response = await self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/image",
                data=data,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    async def send_msg(self, msg: str) -> EmoMessageInfo:
        payload = {"text": msg}
        response = await self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def send_stamp(
        self, stamp_id: str, msg: Optional[str] = None
    ) -> EmoMessageInfo:
        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        response = await self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def send_original_motion(
        self, motion_data: Union[str, dict]
    ) -> EmoMessageInfo:
        if type(motion_data) == str:
            with open(motion_data) as f:
                payload = json.load(f)
        else:
            payload = motion_data
        response = await self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def change_led_color(self, color: Color) -> EmoMessageInfo:
        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        response = await self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def move_to(self, head: Head) -> EmoMessageInfo:
        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        response = await self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def send_motion(self, motion_id: str) -> EmoMessageInfo:
        payload = {"uuid": motion_id}
        response = await self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def get_emo_settings(self) -> EmoSettingsInfo:
        response = await self.base_client._get(
            "/v1/rooms/" + self.room_id + "/emo/settings"
        )
        return EmoSettingsInfo(**response)


class BizBasicAsyncRoom(AsyncRoom):
    async def get_sensor_values(self, sensor_id: str) -> NoReturn:
        raise UnavailableError(self.base_client.PLAN)

    async def send_original_motion(self, motion_data: Union[str, dict]) -> NoReturn:
        raise UnavailableError(self.base_client.PLAN)

    async def change_led_color(self, color: Color) -> NoReturn:
        raise UnavailableError(self.base_client.PLAN)

    async def move_to(self, head: Head) -> NoReturn:
        raise UnavailableError(self.base_client.PLAN)

    async def send_motion(self, motion_id: str) -> NoReturn:
        raise UnavailableError(self.base_client.PLAN)


class BizAdvancedAsyncRoom(AsyncRoom):
    pass
