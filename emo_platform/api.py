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
    EmoWebhookInfo,
)

EMO_PLATFORM_PATH = os.path.abspath(os.path.dirname(__file__))


class EmoWebhook(BaseModel):
    request_id: str
    uuid: str
    serial_number: str
    nickname: str
    timestamp: int
    event: str
    data: dict
    receiver: str


class PostContentType:
    APPLICATION_JSON = "application/json"
    MULTIPART_FORMDATA = None


class Client:
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
        with open(self.TOKEN_FILE, "r") as f:
            tokens = json.load(f)
        refresh_token = tokens["refresh_token"]

        if refresh_token != "":
            try:
                res_tokens = self.get_access_token(refresh_token)
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
                res_tokens = self.get_access_token(refresh_token)
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
        payload = {"refresh_token": refresh_token}
        response = self._post(
            "/oauth/token/refresh", json.dumps(payload), update_tokens=False
        )
        return EmoTokens(**response)

    def get_account_info(self) -> dict:
        response = self._get("/v1/me")
        return EmoAccountInfo(**response)

    def delete_account_info(self) -> dict:
        response = self._delete("/v1/me")
        return EmoAccountInfo(**response)

    def get_rooms_list(self) -> dict:
        response = self._get("/v1/rooms")
        return EmoRoomInfo(**response)

    def get_rooms_id(self) -> list:
        result = self._get("/v1/rooms")
        try:
            room_number = len(result["rooms"])
        except KeyError:
            raise NoRoomError("Get no room id.")
        rooms_id = [result["rooms"][i]["uuid"] for i in range(room_number)]
        self.room_id_list = rooms_id + [self.DEFAULT_ROOM_ID]
        return rooms_id

    def create_room_client(self, room_id: str):
        return Room(self, room_id)

    def get_stamps_list(self) -> dict:
        response = self._get("/v1/stamps")
        return EmoStampsInfo(**response)

    def get_motions_list(self) -> dict:
        response = self._get("/v1/motions")
        return EmoMotionsInfo(**response)

    def get_webhook_setting(self) -> dict:
        response = self._get("/v1/webhook")
        return EmoWebhookInfo(**response)

    def change_webhook_setting(self, webhook: WebHook) -> dict:
        payload = {"description": webhook.description, "url": webhook.url}
        response = self._put("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def register_webhook_event(self, events: List[str]) -> dict:
        payload = {"events": events}
        response = self._put("/v1/webhook/events", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def create_webhook_setting(self, webhook: WebHook) -> dict:
        payload = {"description": webhook.description, "url": webhook.url}
        response = self._post("/v1/webhook", json.dumps(payload))
        return EmoWebhookInfo(**response)

    def delete_webhook_setting(self) -> dict:
        response = self._delete("/v1/webhook")
        return EmoWebhookInfo(**response)

    def event(
        self, event: str, room_id_list: List[str] = [DEFAULT_ROOM_ID]
    ) -> Callable:
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
        response = self.register_webhook_event(list(self.webhook_events_cb.keys()))
        secret_key = response.secret

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
    def __init__(self, base_client: Client, room_id: str):
        self.base_client = base_client
        self.room_id = room_id

    def get_msgs(self, ts: int = None) -> dict:
        params = {"before": ts} if ts else {}
        response = self.base_client._get(
            "/v1/rooms/" + self.room_id + "/messages", params=params
        )
        return EmoMsgsInfo(**response)

    def get_sensors_list(self) -> dict:
        response = self.base_client._get("/v1/rooms/" + self.room_id + "/sensors")
        return EmoSensorsInfo(**response)

    def get_sensor_values(self, sensor_id: str) -> dict:
        response = self.base_client._get(
            "/v1/rooms/" + self.room_id + "/sensors/" + sensor_id + "/values"
        )
        return EmoRoomSensorInfo(**response)

    def send_audio_msg(self, audio_data_path: str) -> dict:
        with open(audio_data_path, "rb") as audio_data:
            files = {"audio": audio_data}
            response = self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/audio",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    def send_image(self, image_data_path: str) -> dict:
        with open(image_data_path, "rb") as image_data:
            files = {"image": image_data}
            response = self.base_client._post(
                "/v1/rooms/" + self.room_id + "/messages/image",
                files=files,
                content_type=PostContentType.MULTIPART_FORMDATA,
            )
            return EmoMessageInfo(**response)

    def send_msg(self, msg: str) -> dict:
        payload = {"text": msg}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/text", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_stamp(self, stamp_id: str, msg: Optional[str] = None) -> dict:
        payload = {"uuid": stamp_id}
        if msg:
            payload["text"] = msg
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/messages/stamp", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_original_motion(self, file_path: str) -> dict:
        with open(file_path) as f:
            payload = json.load(f)
            response = self.base_client._post(
                "/v1/rooms/" + self.room_id + "/motions", json.dumps(payload)
            )
            return EmoMessageInfo(**response)

    def change_led_color(self, color: Color) -> dict:
        payload = {"red": color.red, "green": color.green, "blue": color.blue}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/led_color", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def move_to(self, head: Head) -> dict:
        payload = {"angle": head.angle, "vertical_angle": head.vertical_angle}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/move_to", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def send_motion(self, motion_id: str) -> dict:
        payload = {"uuid": motion_id}
        response = self.base_client._post(
            "/v1/rooms/" + self.room_id + "/motions/preset", json.dumps(payload)
        )
        return EmoMessageInfo(**response)

    def get_emo_settings(self) -> dict:
        response = self.base_client._get("/v1/rooms/" + self.room_id + "/emo/settings")
        return EmoSettingsInfo(**response)
