import unittest
import os, json
import responses
from functools import partial
from emo_platform import Client
from emo_platform.exceptions import (
    NoRefreshTokenError,
    NoRoomError,
    UnauthorizedError,
    http_error_handler,
)

EMO_PLATFORM_TEST_PATH = os.path.abspath(os.path.dirname(__file__))
TOKEN_FILE = f'{EMO_PLATFORM_TEST_PATH}/../emo_platform/tokens/emo-platform-api.json'
class TestGetTokens(unittest.TestCase):

	def setUp(self):
		# reset environment variables
		try:
			os.environ.pop("EMO_PLATFORM_API_REFRESH_TOKEN")
		except KeyError:
			pass
		try:
			os.environ.pop("EMO_PLATFORM_API_ACCESS_TOKEN")
		except KeyError:
			pass

		# reset json file
		tokens = {"refresh_token" : "", "access_token" : ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

		self.responses = responses.RequestsMock()
		self.responses.start()


		self.test_endpoint = 'http://test_api.com'

		self.right_refresh_token = 'RIGHT_REFRESH_TOKEN'
		self.right_access_token = 'RIGHT_ACCESS_TOKEN'
		self.wrong_refresh_token = 'WRONG_REFRESH_TOKEN'
		self.wrong_access_token = 'WRONG_ACCESS_TOKEN'

		def refresh_token_callback(request):
			payload = json.loads(request.body)
			if payload['refresh_token'] == self.right_refresh_token:
				body = json.dumps({'access_token': self.right_access_token, 'refresh_token': self.right_refresh_token})
				return 200, {}, body
			else:
				body = json.dumps({})
				return 401, {}, body

		self.responses.add_callback(
			responses.POST,
			self.test_endpoint + '/oauth/token/refresh',
			callback=refresh_token_callback,
			content_type='application/json'
		)

		def request_callback(request):
			body = json.dumps({})
			if request.headers['Authorization'] == 'Bearer ' + self.right_access_token:
				return 200, {}, body
			else:
				return 401, {}, body

		self.responses.add_callback(
			responses.GET,
			self.test_endpoint + '/v1/me',
			callback=request_callback,
			content_type='application/json'
		)

		self.addCleanup(self.responses.stop)
		self.addCleanup(self.responses.reset)

	def test_no_tokens_set(self): # 1*1*1*1 = 1
		with self.assertRaises(NoRefreshTokenError):
			Client(self.test_endpoint)

	def test_right_access_token_json_set(self): # 1*3*3*3 = 27
		# right access_token set to json
		tokens = {"refresh_token" : "", "access_token" : self.right_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

		client = Client(self.test_endpoint)
		self.assertEqual(client.access_token, self.right_access_token)
		client.get_account_info()

	def test_no_access_token_json_set(self): # 1*1*1*1 = 1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

		# right access_token & no refresh token set to env
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
		client = Client(self.test_endpoint)
		# Raise error even if right access_token set to env
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

	def test_wrong_access_token_json_set(self):
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

		# wrong access_token & no refresh token set to json
		# right access_token & no refresh token set to env
		tokens = {"refresh_token" : "", "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		os.environ["ACCESS_TOKEN"] = self.right_access_token

		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

		# wrong access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

		# wrong access_token & right refresh token set to json
		tokens = {"refresh_token" : self.right_refresh_token, "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		client = Client(self.test_endpoint)
		client.get_account_info()

	# def test_refresh_token_env_set(self):
	# 	os.environ['REFRESH_TOKEN'] = self.right_refresh_token
