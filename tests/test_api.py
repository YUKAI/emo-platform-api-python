import json
import os
import time
import unittest
import json
from functools import partial
from threading import Thread

import requests
import responses
from fastapi.testclient import TestClient

from emo_platform import Client
from emo_platform.exceptions import TokenError, NoRoomError, UnauthorizedError

EMO_PLATFORM_TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TOKEN_FILE = f"{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api.json"
PRE_TOKEN_FILE = f"{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api_previous.json"


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

        try:
            os.remove(TOKEN_FILE)
        except:
            pass

        try:
            os.remove(PRE_TOKEN_FILE)
        except:
            pass

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

        self.test_account_info = {
            "name": "test_api",
            "email": "",
            "profile_image": "",
            "uuid": "",
            "plan": "",
        }

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

    def test_no_access_env_token_set(self): # access -
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        with self.assertRaises(TokenError):
            client = Client(self.test_endpoint)

    def test_no_refresh_env_token_set(self): # refresh -
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        with self.assertRaises(TokenError):
            client = Client(self.test_endpoint)

    def test_wr_wa_env_token_set(self): # access x, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        with self.assertRaises(TokenError):
            client.get_account_info()

        # set right refresh token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_rr_wa_env_token_set(self): # access x, refresh o
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # token expired during excuting
        self.right_access_token = "NEW_ACCESS_TOKEN"
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # token expired before restart client
        with open(TOKEN_FILE, "w") as f:
            saved_tokens = {"refresh_token": self.right_refresh_token, "access_token": self.wrong_access_token}
            json.dump(saved_tokens, f)
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_rr_wa_env_token_set_env_reset(self): # access x, refresh o
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # reset os env
        os.environ.pop("EMO_PLATFORM_API_REFRESH_TOKEN")
        os.environ.pop("EMO_PLATFORM_API_ACCESS_TOKEN")
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_rr_wa_env_token_set_env_change(self): # access x, refresh o
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # change access env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # change refresh env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        with self.assertRaises(TokenError):
            client.get_account_info()

    def test_wr_ra_env_token_set(self): # access o, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # token expired
        self.right_access_token = "NEW_ACCESS_TOKEN"
        with self.assertRaises(TokenError):
            client.get_account_info()

        # set right refresh token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_wr_ra_env_token_set_env_reset(self): # access o, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # reset os env
        os.environ.pop("EMO_PLATFORM_API_REFRESH_TOKEN")
        os.environ.pop("EMO_PLATFORM_API_ACCESS_TOKEN")
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

    def test_wr_ra_env_token_set_env_change(self): # access o, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)

        # change access env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        with self.assertRaises(TokenError):
            client.get_account_info()

        # change refresh env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(client.get_account_info(), self.test_account_info)


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

        self.test_webhook_info = {
            "description": "",
            "events": [],
            "status": "",
            "secret": "test_secret_key",
            "url": "",
        }

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

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

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

        for i in range(client._MAX_SAVED_REQUEST_ID):
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
        time.sleep(0.1)
        self.responses.reset()
        self.responses.stop()
        response = requests.post(
            "http://localhost:8005",
            data=json.dumps({
                "request_id": "test_id",
                "uuid": self.room_uuid,
                "serial_number": "test_serial_no",
                "nickname": "test_nickname",
                "timestamp": 0,
                "event": "test_event",
                "data": {},
                "receiver": "test_receiver",
            }),
            headers={
                "x-platform-api-secret": "test_secret_key",
                "Content-Type": "application/json",
                "accept": "*/*",
            },
        )
        self.assertEqual(response.json(), ["success", 200])
        self.assertFalse(self.test_callback_done)
        time.sleep(2)
        self.assertTrue(self.test_callback_done)
