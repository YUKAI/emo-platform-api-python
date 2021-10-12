import asyncio
import json
import os
from functools import partial
from typing import Callable, List, Optional, Union

import aiohttp
import uvicorn  # type: ignore
from fastapi import FastAPI, Request, BackgroundTasks

from emo_platform.api import Client, PostContentType
from emo_platform.exceptions import (
    NoRefreshTokenError,
    UnauthorizedError,
    aiohttp_error_handler,
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


class AsyncClient(Client):
    async def _update_tokens(self) -> None:
        with open(self.TOKEN_FILE, "r") as f:
            tokens = json.load(f)
        refresh_token = tokens["refresh_token"]

        if refresh_token != "":
            try:
                res_tokens = await self._get_access_token(refresh_token)
                self.access_token = res_tokens.access_token
                refresh_token = res_tokens.refresh_token
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
                res_tokens = await self._get_access_token(refresh_token)
                self.access_token = res_tokens.access_token
                refresh_token = res_tokens.refresh_token
                self.headers["Authorization"] = "Bearer " + self.access_token
                tokens["refresh_token"] = refresh_token
                tokens["access_token"] = self.access_token
                with open(self.TOKEN_FILE, "w") as f:
                    json.dump(tokens, f)
            except UnauthorizedError:
                raise NoRefreshTokenError(
                    "Please set new refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN'"
                )

    async def _acheck_http_error(
        self, request: Callable, update_tokens: bool = True
    ) -> dict:
        async with request() as response:
            try:
                response_msg = await response.text()
                with aiohttp_error_handler(response_msg):
                    response.raise_for_status()
            except UnauthorizedError:
                if not update_tokens:
                    raise
            else:
                return await response.json()

        await self._update_tokens()
        async with request() as response:
            response_msg = await response.text()
            with aiohttp_error_handler(response_msg):
                response.raise_for_status()
            return await response.json()

    async def _aget(self, path: str, params: dict = {}) -> dict:
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.get,
                self.endpoint_url + path,
                params=params,
                headers=self.headers,
            )
            return await self._acheck_http_error(request)

    async def _apost(
        self,
        path: str,
        data: Union[str, aiohttp.FormData] = "{}",
        files: Optional[dict] = None,
        content_type: Optional[str] = PostContentType.APPLICATION_JSON,
        update_tokens: bool = True,
    ) -> dict:
        if content_type is None:
            if "Content-Type" in self.headers:
                self.headers.pop("Content-Type")
        else:
            self.headers["Content-Type"] = content_type
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.post,
                self.endpoint_url + path,
                data=data,
                headers=self.headers,
            )
            return await self._acheck_http_error(request, update_tokens=update_tokens)

    async def _aput(self, path: str, data: str = "{}") -> dict:
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.put, self.endpoint_url + path, data=data, headers=self.headers
            )
            return await self._acheck_http_error(request)

    async def _adelete(self, path: str) -> dict:
        async with aiohttp.ClientSession() as session:
            request = partial(
                session.delete, self.endpoint_url + path, headers=self.headers
            )
            return await self._acheck_http_error(request)

    async def _get_access_token(self, refresh_token: str) -> EmoTokens:
        payload = {"refresh_token": refresh_token}
        response = await self._apost(
            "/oauth/token/refresh", json.dumps(payload), update_tokens=False
        )
        return EmoTokens(**response)

    async def get_account_info(self) -> EmoAccountInfo:
        response = await self._aget("/v1/me")
        return EmoAccountInfo(**response)

    async def delete_account_info(self) -> EmoAccountInfo:
        response = await self._adelete("/v1/me")
        return EmoAccountInfo(**response)

    async def get_rooms_list(self) -> EmoRoomInfo:
        response = await self._aget("/v1/rooms")
        return EmoRoomInfo(**response)

    def create_room_client(self, room_id: str):
        return Room(self, room_id)

    async def get_stamps_list(self) -> EmoStampsInfo:
        response = await self._aget("/v1/stamps")
        return EmoStampsInfo(**response)

    async def get_motions_list(self) -> EmoMotionsInfo:
        response = await self._aget("/v1/motions")
        return EmoMotionsInfo(**response)

    async def get_webhook_setting(self) -> EmoWebhookInfo:
        response = await self._aget("/v1/webhook")
        return EmoWebhookInfo(**response)

    async def change_webhook_setting(self, webhook: WebHook) -> EmoWebhookInfo:
        payload = {"description": webhook.description, "url": webhook.url}
        response = await self._aput("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    async def delete_webhook_setting(self) -> EmoWebhookInfo:
        response = await self._adelete("/v1/webhook")
        return EmoWebhookInfo(**response)

    async def start_webhook_event(
        self, host: str = "localhost", port: int = 8000, tasks: List[asyncio.Task] = []
    ) -> None:
        response = self.register_webhook_event(list(self.webhook_events_cb.keys()))
        secret_key = response.secret

        self.app = FastAPI()

        @self.app.post("/")
        async def emo_callback(request: Request, body: EmoWebhookBody, background_tasks: BackgroundTasks):
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
                    background_tasks.add_task(cb_func, body)
                    self.request_id_deque.append(body.request_id)
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


class Room:
    def __init__(self, base_client: AsyncClient, room_id: str):
        self.base_client = base_client
        self.room_id = room_id

    async def get_msgs(self, ts: int = None) -> EmoMsgsInfo:
        params = {"before": ts} if ts else {}
        response = await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )
        return EmoMsgsInfo(**response)

    async def get_sensors_list(self) -> EmoSensorsInfo:
        response = await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/sensors"
        )
        return EmoSensorsInfo(**response)

    async def get_sensor_values(self, sensor_id: str) -> EmoRoomSensorInfo:
        response = await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )
        return EmoRoomSensorInfo(**response)

    async def send_audio_msg(self, audio_data_path: str) -> EmoMessageInfo:
        with open(audio_data_path, "rb") as audio_data:
            data = aiohttp.FormData()
            data.add_field("audio", audio_data, content_type="multipart/form-data")
            response = await self.base_client._apost(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                data=data,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    async def send_image(self, image_data_path: str) -> EmoMessageInfo:
        with open(image_data_path, "rb") as image_data:
            data = aiohttp.FormData()
            data.add_field("image", image_data, content_type="multipart/form-data")
            response = await self.base_client._apost(
                "/v1/rooms/" + self.room_id + "/messages/image",
                data=data,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    async def send_msg(self, msg: str) -> EmoMessageInfo:
        payload = {"text": msg}
        response = await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def send_stamp(
        self, stamp_id: str, msg: Optional[str] = None
    ) -> EmoMessageInfo:
        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        response = await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def send_original_motion(self, file_path: str) -> EmoMessageInfo:
        with open(file_path) as f:
            payload = json.load(f)
            response = await self.base_client._apost(
                "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
            )
            return EmoMessageInfo(**response)

    async def change_led_color(self, color: Color) -> EmoMessageInfo:
        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        response = await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def move_to(self, head: Head) -> EmoMessageInfo:
        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        response = await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def send_motion(self, motion_id: str) -> EmoMessageInfo:
        payload = {"uuid": motion_id}
        response = await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    async def get_emo_settings(self) -> EmoSettingsInfo:
        response = await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/emo/settings"
        )
        return EmoSettingsInfo(**response)
