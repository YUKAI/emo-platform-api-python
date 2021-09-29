from aiohttp import web, ClientSession
import os, time
from functools import partial
from threading import Thread
import unittest
import json
import asyncio
import responses
from emo_platform import AsyncClient as Client
from emo_platform.exceptions import (
	NoRefreshTokenError,
	NoRoomError,
	UnauthorizedError,
)

EMO_PLATFORM_TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TOKEN_FILE = f"{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api.json"

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

		# reset json file
		tokens = {"refresh_token": "", "access_token": ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

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
					status = 200,
					content_type="application/json",
					body = body
				)
			else:
				body = json.dumps({})
				return web.Response(
					status = 401,
					content_type="application/json",
					body = body
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
					status = 200,
					content_type="application/json",
					body = json.dumps(self.test_account_info)
				)
			else:
				return web.Response(
					status = 401,
					content_type="application/json",
					body = json.dumps({})
				)

		self.test_account_info = {"account_info": "test_api"}

	def init_room_server(self):
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

	async def test_right_access_token_json_set(self):  # 3*3*3*3
		# right access_token set to json
		tokens = {"refresh_token": "", "access_token": self.right_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

		client = Client(self.test_endpoint)
		self.assertEqual(client.access_token, self.right_access_token)
		self.assertEqual(await client.get_account_info(), self.test_account_info)

	async def test_w_a_r_f_json_set(self):  # 1*3*1*3
		# wrong access_token & right refresh token set to json
		tokens = {
			"refresh_token": self.right_refresh_token,
			"access_token": self.wrong_access_token,
		}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		client = Client(self.test_endpoint)
		self.assertEqual(await client.get_account_info(), self.test_account_info)
		self.assertEqual(client.access_token, self.right_access_token)

	async def test_w_a_w_f_json_r_f_env_set(self):  # 1*3*1*1
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
		self.assertEqual(await client.get_account_info(), self.test_account_info)

	async def test_w_a_w_f_json_w_f_env_set(self):  # 1*3*1*1
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
			await client.get_account_info()

	async def test_w_a_w_f_json_n_f_env_set(self):  # 1*3*1*1
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
			await client.get_account_info()

	async def test_w_a_n_f_json_r_f_env_set(self):  # 1*3*1*1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token": "", "access_token": self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(await client.get_account_info(), self.test_account_info)

	async def test_w_a_n_f_json_w_f_env_set(self):  # 1*3*1*1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token": "", "access_token": self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## wrong refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			await client.get_account_info()

	async def test_w_a_n_f_json_n_f_env_set(self):  # 1*3*1*1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token": "", "access_token": self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## no refresh token set to env
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			await client.get_account_info()

	async def test_right_access_token_env_set(self):  # 1*1*3*3
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
		client = Client(self.test_endpoint)
		self.assertEqual(await client.get_account_info(), self.test_account_info)

	async def test_n_a_r_f_json_set(self):  # 1*2*1*3
		# no access_token & right refresh token set to json
		tokens = {"refresh_token": self.right_refresh_token, "access_token": ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		client = Client(self.test_endpoint)
		self.assertEqual(await client.get_account_info(), self.test_account_info)
		self.assertEqual(client.access_token, self.right_access_token)

	async def test_n_a_w_f_json_r_f_env(self):  # 1*2*1*1
		# no access_token & wrong refresh token set to json
		tokens = {"refresh_token": self.wrong_refresh_token, "access_token": ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(await client.get_account_info(), self.test_account_info)

	async def test_n_a_w_f_json_w_f_env(self):  # 1*2*1*1
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
			await client.get_account_info()

	async def test_n_a_w_f_json_n_f_env(self):  # 1*2*1*1
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
			await client.get_account_info()

	async def test_n_a_n_f_json_r_f_env(self):  # 1*2*1*1
		# no access_token & no refresh token set to json
		tokens = {"refresh_token": "", "access_token": ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(await client.get_account_info(), self.test_account_info)

	async def test_n_a_n_f_json_w_f_env(self):  # 1*2*1*1
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
			await client.get_account_info()

	async def test_n_a_n_f_json_n_f_env(self):  # 1*2*1*1
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
			await client.get_account_info()

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
				await client._acheck_http_error(request=request), self.test_account_info
			)


	async def test_http_request_fail(self):
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

		client = Client(self.test_endpoint)
		async with ClientSession() as session:
			request = partial(
				session.get,
				self.test_endpoint + "/v1/me",
				headers={"Authorization": ""}
			)
			with self.assertRaises(UnauthorizedError):
				await client._acheck_http_error(request=request, update_tokens=False)

	async def test_http_request_success_with_retry(self):
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

		client = Client(self.test_endpoint)
		async with ClientSession() as session:
			request = partial(
				session.get,
				self.test_endpoint + "/v1/me",
				headers=client.headers
			)
			self.assertEqual(
				await client._acheck_http_error(request=request), self.test_account_info
			)


class TestGetRoomsId(unittest.TestCase, TestBaseClass):

	def setUp(self):
		self.init_server()
		self.init_room_server()

		self.reset_tokens()
		self.set_tokens()

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

		self.assertEqual(await client.webhook_events_cb["test_event"][""](), return_val)

		return_val = "test_webhook_callback_new"

		@client.event("test_event")
		async def test_webhook_callback_new():
			return return_val

		self.assertEqual(await client.webhook_events_cb["test_event"][""](), return_val)

	# TODO: Uncomment after merging non async version
	# async def test_register_event_with_room_id(self):
	# 	client = Client(self.test_endpoint)
	# 	old_room_uuid = self.test_rooms_info["rooms"][0]["uuid"]
	# 	new_room_uuid = "new_room_uuid"
	# 	self.test_rooms_info["rooms"].append({"uuid": new_room_uuid})

	# 	return_val = "test_webhook_callback"

	# 	@client.event("test_event", [old_room_uuid])
	# 	async def test_webhook_callback():
	# 		return return_val

	# 	return_val_new = "test_webhook_callback_new"

	# 	@client.event("test_event", [new_room_uuid])
	# 	async def test_webhook_callback_new():
	# 		return return_val_new

	# 	self.assertEqual(
	# 		await client.webhook_events_cb["test_event"][old_room_uuid](), return_val
	# 	)
	# 	self.assertEqual(
	# 		await client.webhook_events_cb["test_event"][new_room_uuid](), return_val_new
	# 	)

	async def test_register_event_with_nonexistent_room_id(self):
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRoomError):

			@client.event("test_event", ["nonexistent_room_id"])
			async def test_webhook_callback():
				pass
