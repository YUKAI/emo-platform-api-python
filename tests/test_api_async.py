import asyncio
import json
import os
import unittest
from functools import partial

import responses
from aiohttp import ClientSession, web

from emo_platform import AsyncClient as Client
from emo_platform.exceptions import NoRoomError, TokenError, UnauthorizedError
from emo_platform.models import Tokens

EMO_PLATFORM_TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TOKEN_FILE = f"{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api.json"
PRE_TOKEN_FILE = (
    f"{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api_previous.json"
)


class TestBaseClass(object):
    def reset_tokens(self):
        # reset environment variable
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
        except Exception:
            pass

        try:
            os.remove(PRE_TOKEN_FILE)
        except Exception:
            pass

        self.right_refresh_token = "RIGHT_REFRESH_TOKEN"
        self.right_access_token = "RIGHT_ACCESS_TOKEN"
        self.wrong_refresh_token = "WRONG_REFRESH_TOKEN"
        self.wrong_access_token = "WRONG_ACCESS_TOKEN"

    def init_server(self):

        self.test_endpoint = "http://0.0.0.0:8080"
        self.routes = web.RouteTableDef()

        @self.routes.post("/oauth/token/refresh")
        async def a_refresh_token_callback(request):
            payload = await request.json()
            if payload["refresh_token"] == self.right_refresh_token:
                body = json.dumps(
                    {
                        "access_token": self.right_access_token,
                        "refresh_token": self.right_refresh_token,
                    }
                )
                return web.Response(
                    status=200, content_type="application/json", body=body
                )
            else:
                body = json.dumps({})
                return web.Response(
                    status=401, content_type="application/json", body=body
                )

        self.responses = responses.RequestsMock()
        self.responses.start()

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

        @self.routes.get("/v1/me")
        async def account_info_callback(request):
            if request.headers["Authorization"] == "Bearer " + self.right_access_token:
                return web.Response(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(self.test_account_info),
                )
            else:
                return web.Response(
                    status=401, content_type="application/json", body=json.dumps({})
                )

        self.test_account_info = {
            "name": "test_api",
            "email": "",
            "profile_image": "",
            "uuid": "",
            "plan": "",
        }

    def init_room_server(self):

        test_room_info = {
            "uuid":"52b0e129-2512-4696-9d06-8ddb842ba6ce",
            "name":"test_room",
            "room_type":"test",
            "room_members":[]
        }
        self.test_rooms_info = {
            "listing" : {"offset":0, "limit":0, "total":0},
            "rooms" : [test_room_info]
        }

        @self.routes.get("/v1/rooms")
        async def rooms_info_callback(request):
            if request.headers["Authorization"] == "Bearer " + self.right_access_token:
                return web.Response(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(self.test_rooms_info),
                )
            else:
                return web.Response(
                    status=401, content_type="application/json", body=json.dumps({})
                )

    async def aiohttp_server_start(self):
        self.app = web.Application()
        self.app.add_routes(self.routes)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner)
        await self.site.start()

    async def aiohttp_server_stop(self):
        await self.site.stop()

    def set_tokens(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token


class TestGetTokens(unittest.IsolatedAsyncioTestCase, TestBaseClass):
    async def asyncSetUp(self):
        self.init_server()
        await self.aiohttp_server_start()
        self.reset_tokens()

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    async def asyncTearDown(self):
        await self.aiohttp_server_stop()

    async def test_wr_wa_env_token_set(self):  # access x, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        with self.assertRaises(TokenError):
            await client.get_account_info()

        # set right refresh token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_rr_wa_env_token_set(self):  # access x, refresh o
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # token expired during excuting
        self.right_access_token = "NEW_ACCESS_TOKEN"
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # token expired before restart client
        with open(TOKEN_FILE, "w") as f:
            saved_tokens = {
                "refresh_token": self.right_refresh_token,
                "access_token": self.wrong_access_token,
            }
            json.dump(saved_tokens, f)
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_rr_wa_env_token_set_env_reset(self):  # access x, refresh o
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # reset os env
        os.environ.pop("EMO_PLATFORM_API_REFRESH_TOKEN")
        os.environ.pop("EMO_PLATFORM_API_ACCESS_TOKEN")
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_rr_wa_env_token_set_env_change(self):  # access x, refresh o
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # change access env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # change refresh env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        with self.assertRaises(TokenError):
            await client.get_account_info()

    async def test_wr_ra_env_token_set(self):  # access o, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # token expired
        self.right_access_token = "NEW_ACCESS_TOKEN"
        with self.assertRaises(TokenError):
            await client.get_account_info()

        # set right refresh token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_wr_ra_env_token_set_env_reset(self):  # access o, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # reset os env
        os.environ.pop("EMO_PLATFORM_API_REFRESH_TOKEN")
        os.environ.pop("EMO_PLATFORM_API_ACCESS_TOKEN")
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_wr_ra_env_token_set_env_change(self):  # access o, refresh x
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        # change access env
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token
        client = Client(self.test_endpoint)
        with self.assertRaises(TokenError):
            await client.get_account_info()

        # change refresh env
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_set_reset_args(self):
        tokens = Tokens(refresh_token=self.right_refresh_token)
        client = Client(self.test_endpoint, tokens=tokens)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        tokens = Tokens(access_token=self.right_access_token)
        client = Client(self.test_endpoint, tokens=tokens)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        client = Client(self.test_endpoint)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

    async def test_is_server(self):
        tokens = Tokens(
            refresh_token=self.right_refresh_token,
            access_token=self.wrong_access_token
        )
        client = Client(self.test_endpoint, tokens=tokens, is_server=True)
        self.assertEqual(await client.get_account_info(), self.test_account_info)

        with self.assertRaises(TokenError):
            client = Client(self.test_endpoint, is_server=True)

class TestCheckHttpError(unittest.IsolatedAsyncioTestCase, TestBaseClass):
    async def asyncSetUp(self):
        self.init_server()
        await self.aiohttp_server_start()
        self.reset_tokens()

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    async def asyncTearDown(self):
        await self.aiohttp_server_stop()

    async def test_http_request_success(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token

        client = Client(self.test_endpoint)
        async with ClientSession() as session:
            request = partial(
                session.get,
                self.test_endpoint + "/v1/me",
                headers={"Authorization": "Bearer " + self.right_access_token},
            )
            self.assertEqual(
                await client._check_http_error(request=request), self.test_account_info
            )

    async def test_http_request_fail(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

        client = Client(self.test_endpoint)
        async with ClientSession() as session:
            request = partial(
                session.get,
                self.test_endpoint + "/v1/me",
                headers={"Authorization": ""},
            )
            with self.assertRaises(UnauthorizedError):
                await client._check_http_error(request=request, update_tokens=False)

    async def test_http_request_success_with_retry(self):
        os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
        os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

        client = Client(self.test_endpoint)
        async with ClientSession() as session:
            request = partial(
                session.get, self.test_endpoint + "/v1/me", headers=client._client._headers
            )
            self.assertEqual(
                await client._check_http_error(request=request), self.test_account_info
            )


class TestGetRoomsId(unittest.IsolatedAsyncioTestCase, TestBaseClass):
    async def asyncSetUp(self):
        self.init_server()
        self.init_room_server()
        await self.aiohttp_server_start()

        self.reset_tokens()
        self.set_tokens()

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    async def asyncTearDown(self):
        await self.aiohttp_server_stop()

    async def test_get_rooms_id(self):
        client = Client(self.test_endpoint)
        rooms_id = await client.get_rooms_id()
        for room in self.test_rooms_info["rooms"]:
            self.assertTrue(room["uuid"] in rooms_id)

    async def test_get_no_rooms_id(self):
        client = Client(self.test_endpoint)
        self.test_rooms_info["rooms"] = []
        with self.assertRaises(NoRoomError):
            await client.get_rooms_id()


class TestWebhookRegister(unittest.IsolatedAsyncioTestCase, TestBaseClass):
    async def asyncSetUp(self):
        self.init_server()
        self.init_room_server()

        self.reset_tokens()
        self.set_tokens()

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    async def test_register_event(self):
        client = Client(self.test_endpoint)
        return_val = "test_webhook_callback"

        @client.event("test_event")
        async def test_webhook_callback():
            return return_val

        self.assertEqual(await client._client._webhook_events_cb["test_event"][""](), return_val)

        return_val = "test_webhook_callback_new"

        @client.event("test_event")
        async def test_webhook_callback_new():
            return return_val

        self.assertEqual(await client._client._webhook_events_cb["test_event"][""](), return_val)

    async def test_register_event_with_room_id(self):
        client = Client(self.test_endpoint)
        old_room_uuid = self.test_rooms_info["rooms"][0]["uuid"]
        new_room_uuid = "new_room_uuid"
        self.test_rooms_info["rooms"].append({"uuid": new_room_uuid})

        return_val = "test_webhook_callback"

        @client.event("test_event", [old_room_uuid])
        async def test_webhook_callback():
            return return_val

        return_val_new = "test_webhook_callback_new"

        @client.event("test_event", [new_room_uuid])
        async def test_webhook_callback_new():
            return return_val_new

        self.assertEqual(
            await client._client._webhook_events_cb["test_event"][old_room_uuid](), return_val
        )
        self.assertEqual(
            await client._client._webhook_events_cb["test_event"][new_room_uuid](),
            return_val_new,
        )
