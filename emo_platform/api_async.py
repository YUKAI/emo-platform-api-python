import asyncio
import json
import os
from functools import partial
from typing import Callable, List, Optional

import aiohttp
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks

from emo_platform.api import Client, EmoWebhook, PostContentType
from emo_platform.exceptions import (
    NoRefreshTokenError,
    UnauthorizedError,
    aiohttp_error_handler,
)
from emo_platform.models import Color, Head, WebHook


class AsyncClient(Client):
    async def _update_tokens(self) -> None:
        with open(self.TOKEN_FILE, "r") as f:
            tokens = json.load(f)
        refresh_token = tokens["refresh_token"]

        if refresh_token != "":
            try:
                refresh_token, self.access_token = await self._get_access_token(
                    refresh_token
                )
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
                refresh_token, self.access_token = await self._get_access_token(
                    refresh_token
                )
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
                with aiohttp_error_handler():
                    response.raise_for_status()
            except UnauthorizedError:
                if not update_tokens:
                    raise UnauthorizedError(
                        "Unauthorized error while getting access_token"
                    )
                await self._update_tokens()
                response = await request()
                with aiohttp_error_handler():
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
        data: dict = {},
        files: Optional[dict] = None,
        content_type: PostContentType = PostContentType.APPLICATION_JSON,
        update_tokens: bool = True,
    ) -> dict:
        if content_type is None:
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

    async def _aput(self, path: str, data: dict = {}) -> dict:
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

    async def _get_access_token(self, refresh_token: str) -> tuple:
        payload = {"refresh_token": refresh_token}
        result = await self._apost(
            "/oauth/token/refresh", json.dumps(payload), update_tokens=False
        )
        return result["refresh_token"], result["access_token"]

    async def get_account_info(self) -> dict:
        return await self._aget("/v1/me")

    async def delete_account_info(self) -> dict:
        return await self._adelete("/v1/me")

    async def get_rooms_list(self) -> dict:
        return await self._aget("/v1/rooms")

    def create_room_client(self, room_id: str):
        return Room(self, room_id)

    async def get_stamps_list(self) -> dict:
        return await self._aget("/v1/stamps")

    async def get_motions_list(self) -> dict:
        return await self._aget("/v1/motions")

    async def get_webhook_setting(self) -> dict:
        return await self._aget("/v1/webhook")

    async def change_webhook_setting(self, webhook: WebHook) -> dict:
        payload = {"description": webhook.description, "url": webhook.url}
        return await self._aput("/v1/webhook", json.dumps(payload))

    async def delete_webhook_setting(self) -> dict:
        return await self._adelete("/v1/webhook")

    async def start_webhook_event(
        self, host: str = "localhost", port: int = 8000, tasks: List[asyncio.Task] = []
    ) -> None:
        response = self.register_webhook_event(list(self.webhook_events_cb.keys()))
        secret_key = response["secret"]

        self.app = FastAPI()

        @self.app.post("/")
        async def emo_callback(request: Request, body: EmoWebhook, background_tasks: BackgroundTasks):
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
    def __init__(self, base_client: Client, room_id: str):
        self.base_client = base_client
        self.room_id = room_id

    async def get_msgs(self, ts: int = None) -> dict:
        params = {"before": ts} if ts else {}
        return await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )

    async def get_sensors_list(self) -> dict:
        return await self.base_client._aget("/v1/rooms/" + self.room_id + "/sensors")

    async def get_sensor_values(self, sensor_id: str) -> dict:
        return await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )

    async def send_audio_msg(self, audio_data_path: str) -> dict:
        with open(audio_data_path, "rb") as audio_data:
            data = aiohttp.FormData()
            data.add_field("audio", audio_data, content_type="multipart/form-data")
            return await self.base_client._apost(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                data=data,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )

    async def send_image(self, image_data_path: str) -> dict:
        with open(image_data_path, "rb") as image_data:
            data = aiohttp.FormData()
            data.add_field("image", image_data, content_type="multipart/form-data")
            # files = {"image": image_data}
            return await self.base_client._apost(
                "/v1/rooms/" + self.room_id + "/messages/image",
                data=data,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )

    async def send_msg(self, msg: str) -> dict:
        payload = {"text": msg}
        return await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )

    async def send_stamp(self, stamp_id: str, msg: Optional[str] = None) -> dict:
        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        return await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )

    async def send_original_motion(self, file_path: str) -> dict:
        with open(file_path) as f:
            payload = json.load(f)
            return await self.base_client._apost(
                "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
            )

    async def change_led_color(self, color: Color) -> dict:
        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        return await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )

    async def move_to(self, head: Head) -> dict:
        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        return await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )

    async def send_motion(self, motion_id: str) -> dict:
        payload = {"uuid": motion_id}
        return await self.base_client._apost(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )

    async def get_emo_settings(self) -> dict:
        return await self.base_client._aget(
            "/v1/rooms/" + self.room_id + "/emo/settings"
        )
