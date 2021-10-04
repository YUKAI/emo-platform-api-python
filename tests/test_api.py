import json
import os
import time
import unittest
from functools import partial
from threading import Thread

import requests
import responses
from fastapi.testclient import TestClient

from emo_platform import Client
from emo_platform.exceptions import (
    NoRefreshTokenError,
    NoRoomError,
    UnauthorizedError,
)

EMO_PLATFORM_TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TOKEN_FILE = f"{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api.json"


class TestBaseClass(object):
    def init(self):
        try:
            os.environ.pop("EMO_PLATFORM_API_REFRESH_TOKEN")
        except KeyError:
            pass
        try:
            os.environ.pop("EMO_PLATFORM_API_ACCESS_TOKEN")
        except KeyError:
            pass

        # reset json file
        tokens = {"refresh_token": "", "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)

        self.responses = responses.RequestsMock()
        self.responses.start()

        self.test_endpoint = "http://test_api.com"

        self.right_refresh_token = "RIGHT_REFRESH_TOKEN"
        self.right_access_token = "RIGHT_ACCESS_TOKEN"
        self.wrong_refresh_token = "WRONG_REFRESH_TOKEN"
        self.wrong_access_token = "WRONG_ACCESS_TOKEN"

        def refresh_token_callback(request):
            payload = json.loads(request.body)
            if payload["refresh_token"] == self.right_refresh_token:
                body = json.dumps(
                    {
                        "access_token": self.right_access_token,
                        "refresh_token": self.right_refresh_token,
                    }
                )
                return 200, {}, body
            else:
                body = json.dumps({})
                return 401, {}, body

        self.responses.add_callback(
            responses.POST,
            self.test_endpoint + "/oauth/token/refresh",
            callback=refresh_token_callback,
            content_type="application/json",
        )

        self.test_account_info = {"account_info": "test_api"}

        def account_info_callback(request):
            if request.headers["Authorization"] == "Bearer " + self.right_access_token:
                return 200, {}, json.dumps(self.test_account_info)
            else:
                return 401, {}, json.dumps({})

        self.responses.add_callback(
            responses.GET,
            self.test_endpoint + "/v1/me",
            callback=account_info_callback,
            content_type="application/json",
        )

    def room_init(self):
        self.test_rooms_info = {
            "rooms": [{"uuid": "52b0e129-2512-4696-9d06-8ddb842ba6ce"}]
        }

        def rooms_info_callback(request):
            if request.headers["Authorization"] == "Bearer " + self.right_access_token:
                return 200, {}, json.dumps(self.test_rooms_info)
            else:
                return 401, {}, json.dumps({})

        self.responses.add_callback(
            responses.GET,
            self.test_endpoint + "/v1/rooms",
            callback=rooms_info_callback,
            content_type="application/json",
        )

    def set_tokens(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token


class TestGetTokens(unittest.TestCase, TestBaseClass):
    def setUp(self):
        super().init()
        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    def test_right_access_token_json_set(self):  # 3*3*3*3
        # right access_token set to json
        tokens = {"refresh_token": "", "access_token": self.right_access_token}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)

        client = Client(self.test_endpoint)
        self.assertEqual(client.access_token, self.right_access_token)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_w_a_r_f_json_set(self):  # 1*3*1*3
        # wrong access_token & right refresh token set to json
        tokens = {
            "refresh_token": self.right_refresh_token,
            "access_token": self.wrong_access_token,
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)
        self.assertEqual(client.access_token, self.right_access_token)

    def test_w_a_w_f_json_r_f_env_set(self):  # 1*3*1*1
        # wrong access_token & wrong refresh token set to json
        tokens = {
            "refresh_token": self.wrong_refresh_token,
            "access_token": self.wrong_access_token,
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## right refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_w_a_w_f_json_w_f_env_set(self):  # 1*3*1*1
        # wrong access_token & wrong refresh token set to json
        tokens = {
            "refresh_token": self.wrong_refresh_token,
            "access_token": self.wrong_access_token,
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## wrong refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_w_a_w_f_json_n_f_env_set(self):  # 1*3*1*1
        # wrong access_token & wrong refresh token set to json
        tokens = {
            "refresh_token": self.wrong_refresh_token,
            "access_token": self.wrong_access_token,
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## no refresh token set to env
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_w_a_n_f_json_r_f_env_set(self):  # 1*3*1*1
        # wrong access_token & no refresh token set to json
        tokens = {"refresh_token": "", "access_token": self.wrong_access_token}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## right refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_w_a_n_f_json_w_f_env_set(self):  # 1*3*1*1
        # wrong access_token & no refresh token set to json
        tokens = {"refresh_token": "", "access_token": self.wrong_access_token}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## wrong refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_w_a_n_f_json_n_f_env_set(self):  # 1*3*1*1
        # wrong access_token & no refresh token set to json
        tokens = {"refresh_token": "", "access_token": self.wrong_access_token}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## no refresh token set to env
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_right_access_token_env_set(self):  # 1*1*3*3
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_n_a_r_f_json_set(self):  # 1*2*1*3
        # no access_token & right refresh token set to json
        tokens = {"refresh_token": self.right_refresh_token, "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)
        self.assertEqual(client.access_token, self.right_access_token)

    def test_n_a_w_f_json_r_f_env(self):  # 1*2*1*1
        # no access_token & wrong refresh token set to json
        tokens = {"refresh_token": self.wrong_refresh_token, "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## right refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_n_a_w_f_json_w_f_env(self):  # 1*2*1*1
        # no access_token & wrong refresh token set to json
        tokens = {"refresh_token": self.wrong_refresh_token, "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## wrong refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        with self.assertRaises(NoRefreshTokenError):
            client = Client(self.test_endpoint)

        ## set wrong access token set to env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_n_a_w_f_json_n_f_env(self):  # 1*2*1*1
        # no access_token & wrong refresh token set to json
        tokens = {"refresh_token": self.wrong_refresh_token, "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## no refresh token set to env
        with self.assertRaises(NoRefreshTokenError):
            client = Client(self.test_endpoint)

        ## set wrong access token set to env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_n_a_n_f_json_r_f_env(self):  # 1*2*1*1
        # no access_token & no refresh token set to json
        tokens = {"refresh_token": "", "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## right refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_n_a_n_f_json_w_f_env(self):  # 1*2*1*1
        # no access_token & no refresh token set to json
        tokens = {"refresh_token": "", "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## wrong refresh token set to env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        with self.assertRaises(NoRefreshTokenError):
            client = Client(self.test_endpoint)

        ## set wrong access token set to env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()

    def test_n_a_n_f_json_n_f_env(self):  # 1*2*1*1
        # no access_token & no refresh token set to json
        tokens = {"refresh_token": "", "access_token": ""}
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        ## no refresh token set to env
        with self.assertRaises(NoRefreshTokenError):
            client = Client(self.test_endpoint)

        ## set wrong access token set to env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRefreshTokenError):
            client.get_account_info()


class TestCheckHttpError(unittest.TestCase, TestBaseClass):
    def setUp(self):
        super().init()
        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    def test_http_request_success(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token

        client = Client(self.test_endpoint)
        request = partial(
            requests.get,
            self.test_endpoint + "/v1/me",
            headers={"Authorization": "Bearer " + self.right_access_token},
        )
        client._check_http_error(request=request)

    def test_http_request_fail(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

        client = Client(self.test_endpoint)
        request = partial(
            requests.get, self.test_endpoint + "/v1/me", headers={"Authorization": ""}
        )
        with self.assertRaises(UnauthorizedError):
            client._check_http_error(request=request, update_tokens=False)

    def test_http_request_success_with_retry(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

        client = Client(self.test_endpoint)
        request = partial(
            requests.get, self.test_endpoint + "/v1/me", headers=client.headers
        )
        self.assertEqual(
            client._check_http_error(request=request), self.test_account_info
        )


class TestGetRoomsId(unittest.TestCase, TestBaseClass):
    def setUp(self):
        super().init()
        super().room_init()
        super().set_tokens()

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    def test_get_rooms_id(self):
        client = Client(self.test_endpoint)
        for room_uuid in range(10):
            rooms_id = client.get_rooms_id()
            for room in self.test_rooms_info["rooms"]:
                self.assertTrue(room["uuid"] in rooms_id)
            self.test_rooms_info["rooms"].append({"uuid": str(room_uuid)})

    def test_get_no_rooms_id(self):
        client = Client(self.test_endpoint)
        self.test_rooms_info = {}
        with self.assertRaises(NoRoomError):
            client.get_rooms_id()


class TestWebhookRegister(unittest.TestCase, TestBaseClass):
    def setUp(self):
        super().init()
        super().room_init()
        super().set_tokens()

    def test_register_event(self):
        client = Client(self.test_endpoint)
        return_val = "test_webhook_callback"

        @client.event("test_event")
        def test_webhook_callback():
            return return_val

        self.assertEqual(client.webhook_events_cb["test_event"][""](), return_val)

        return_val = "test_webhook_callback_new"

        @client.event("test_event")
        def test_webhook_callback_new():
            return return_val

        self.assertEqual(client.webhook_events_cb["test_event"][""](), return_val)

    def test_register_event_with_room_id(self):
        client = Client(self.test_endpoint)
        old_room_uuid = self.test_rooms_info["rooms"][0]["uuid"]
        new_room_uuid = "new_room_uuid"
        self.test_rooms_info["rooms"].append({"uuid": new_room_uuid})

        return_val = "test_webhook_callback"

        @client.event("test_event", [old_room_uuid])
        def test_webhook_callback():
            return return_val

        return_val_new = "test_webhook_callback_new"

        @client.event("test_event", [new_room_uuid])
        def test_webhook_callback_new():
            return return_val_new

        self.assertEqual(
            client.webhook_events_cb["test_event"][old_room_uuid](), return_val
        )
        self.assertEqual(
            client.webhook_events_cb["test_event"][new_room_uuid](), return_val_new
        )

    def test_register_event_with_nonexistent_room_id(self):
        client = Client(self.test_endpoint)
        with self.assertRaises(NoRoomError):

            @client.event("test_event", ["nonexistent_room_id"])
            def test_webhook_callback():
                pass


class TestWebhookReceive(unittest.TestCase, TestBaseClass):
    def setUp(self):
        super().init()
        super().room_init()
        super().set_tokens()

        self.test_webhook_info = {"secret": "test_secret_key"}

        def webhook_info_callback(request):
            if request.headers["Authorization"] == "Bearer " + self.right_access_token:
                return 200, {}, json.dumps(self.test_webhook_info)
            else:
                return 401, {}, json.dumps({})

        self.responses.add_callback(
            responses.PUT,
            self.test_endpoint + "/v1/webhook/events",
            callback=webhook_info_callback,
            content_type="application/json",
        )

        self.room_uuid = self.test_rooms_info["rooms"][0]["uuid"]

    def test_webhook_receive(self):
        client = Client(self.test_endpoint)

        @client.event("test_event")
        def test_webhook_callback(body):
            self.assertEqual(body.request_id, "test_id")
            self.assertEqual(body.uuid, "52b0e129-2512-4696-9d06-8ddb842ba6ce")
            self.assertEqual(body.serial_number, "test_serial_no")
            self.assertEqual(body.nickname, "test_nickname")
            self.assertEqual(body.timestamp, 0)
            self.assertEqual(body.event, "test_event")
            self.assertEqual(body.data, {})
            self.assertEqual(body.receiver, "test_receiver")

        thread = Thread(target=client.start_webhook_event)
        thread.setDaemon(True)
        thread.start()
        time.sleep(0.01)
        app_client = TestClient(client.app)
        response = app_client.post(
            "/",
            headers={"x-platform-api-secret": "test_secret_key"},
            json={
                "request_id": "test_id",
                "uuid": self.room_uuid,
                "serial_number": "test_serial_no",
                "nickname": "test_nickname",
                "timestamp": 0,
                "event": "test_event",
                "data": {},
                "receiver": "test_receiver",
            },
        )
        self.assertEqual(response.json(), ["success", 200])

    def test_webhook_receive_with_room_id(self):
        client = Client(self.test_endpoint)

        @client.event("test_event", [self.room_uuid])
        def test_webhook_callback(body):
            self.assertEqual(body.request_id, "test_id")
            self.assertEqual(body.uuid, "52b0e129-2512-4696-9d06-8ddb842ba6ce")
            self.assertEqual(body.serial_number, "test_serial_no")
            self.assertEqual(body.nickname, "test_nickname")
            self.assertEqual(body.timestamp, 0)
            self.assertEqual(body.event, "test_event")
            self.assertEqual(body.data, {})
            self.assertEqual(body.receiver, "test_receiver")

        thread = Thread(
            target=client.start_webhook_event,
            args=(
                "localhost",
                8001,
            ),
        )
        thread.setDaemon(True)
        thread.start()
        time.sleep(0.01)
        app_client = TestClient(client.app)
        response = app_client.post(
            "/",
            headers={"x-platform-api-secret": "test_secret_key"},
            json={
                "request_id": "test_id",
                "uuid": self.room_uuid,
                "serial_number": "test_serial_no",
                "nickname": "test_nickname",
                "timestamp": 0,
                "event": "test_event",
                "data": {},
                "receiver": "test_receiver",
            },
        )
        self.assertEqual(response.json(), ["success", 200])

    def test_webhook_receive_with_wrong_room_id(self):
        client = Client(self.test_endpoint)

        @client.event("test_event", [self.room_uuid])
        def test_webhook_callback(body):
            pass

        thread = Thread(
            target=client.start_webhook_event,
            args=(
                "localhost",
                8002,
            ),
        )
        thread.setDaemon(True)
        thread.start()
        time.sleep(0.01)
        app_client = TestClient(client.app)
        response = app_client.post(
            "/",
            headers={"x-platform-api-secret": "test_secret_key"},
            json={
                "request_id": "test_id",
                "uuid": "wrong_room_id",
                "serial_number": "test_serial_no",
                "nickname": "test_nickname",
                "timestamp": 0,
                "event": "test_event",
                "data": {},
                "receiver": "test_receiver",
            },
        )
        self.assertEqual(
            response.json(), ["fail. no callback associated with the room.", 500]
        )

    def test_webhook_receive_with_wrong_secret_key(self):
        client = Client(self.test_endpoint)

        @client.event("test_event")
        def test_webhook_callback(body):
            pass

        thread = Thread(
            target=client.start_webhook_event,
            args=(
                "localhost",
                8003,
            ),
        )
        thread.setDaemon(True)
        thread.start()
        time.sleep(0.01)
        app_client = TestClient(client.app)
        response = app_client.post(
            "/",
            headers={"x-platform-api-secret": "test_wrong_secret_key"},
            json={
                "request_id": "test_id",
                "uuid": self.room_uuid,
                "serial_number": "test_serial_no",
                "nickname": "test_nickname",
                "timestamp": 0,
                "event": "test_event",
                "data": {},
                "receiver": "test_receiver",
            },
        )
        self.assertEqual(response.json(), None)

    def test_webhook_receive_with_same_request_id(self):
        client = Client(self.test_endpoint)

        @client.event("test_event")
        def test_webhook_callback(body):
            pass

        thread = Thread(
            target=client.start_webhook_event,
            args=(
                "localhost",
                8004,
            ),
        )
        thread.setDaemon(True)
        thread.start()
        time.sleep(0.01)
        app_client = TestClient(client.app)
        test_body = {
            "request_id": "test_id",
            "uuid": self.room_uuid,
            "serial_number": "test_serial_no",
            "nickname": "test_nickname",
            "timestamp": 0,
            "event": "test_event",
            "data": {},
            "receiver": "test_receiver",
        }
        response = app_client.post(
            "/", headers={"x-platform-api-secret": "test_secret_key"}, json=test_body
        )
        self.assertEqual(response.json(), ["success", 200])

        response = app_client.post(
            "/", headers={"x-platform-api-secret": "test_secret_key"}, json=test_body
        )
        self.assertEqual(response.json(), None)

        for i in range(client.MAX_SAVED_REQUEST_ID):
            test_body["request_id"] = str(i)
            response = app_client.post(
                "/",
                headers={"x-platform-api-secret": "test_secret_key"},
                json=test_body,
            )
            self.assertEqual(response.json(), ["success", 200])

        test_body["request_id"] = "test_id"
        response = app_client.post(
            "/", headers={"x-platform-api-secret": "test_secret_key"}, json=test_body
        )
        self.assertEqual(response.json(), ["success", 200])

    def test_webhook_receive_with_heavy_process_callback(self):
        client = Client(self.test_endpoint)

        self.test_callback_done = False

        @client.event("test_event")
        def test_webhook_callback(body):
            time.sleep(1)
            self.test_callback_done = True

        thread = Thread(
            target=client.start_webhook_event,
            args=(
                "localhost",
                8005,
            ),
        )
        thread.setDaemon(True)
        thread.start()
        time.sleep(0.01)
        app_client = TestClient(client.app)
        response = app_client.post(
            "/",
            headers={"x-platform-api-secret": "test_secret_key"},
            json={
                "request_id": "test_id",
                "uuid": self.room_uuid,
                "serial_number": "test_serial_no",
                "nickname": "test_nickname",
                "timestamp": 0,
                "event": "test_event",
                "data": {},
                "receiver": "test_receiver",
            },
        )
        self.assertEqual(response.json(), ["success", 200])
        self.assertFalse(self.test_callback_done)
        time.sleep(2)
        self.assertTrue(self.test_callback_done)