import unittest
import os, json
import requests, responses
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

		self.test_account_info = {'account_info' : 'test_api'}
		def account_info_callback(request):
			if request.headers['Authorization'] == 'Bearer ' + self.right_access_token:
				return 200, {}, json.dumps(self.test_account_info)
			else:
				return 401, {}, json.dumps({})

		self.responses.add_callback(
			responses.GET,
			self.test_endpoint + '/v1/me',
			callback=account_info_callback,
			content_type='application/json'
		)



class TestGetTokens(unittest.TestCase, TestBaseClass):

	def setUp(self):
		super().init()
		self.addCleanup(self.responses.stop)
		self.addCleanup(self.responses.reset)

	def test_right_access_token_json_set(self): # 3*3*3*3
		# right access_token set to json
		tokens = {"refresh_token" : "", "access_token" : self.right_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)

		client = Client(self.test_endpoint)
		self.assertEqual(client.access_token, self.right_access_token)
		self.assertEqual(client.get_account_info(), self.test_account_info)


	def test_w_a_r_f_json_set(self): # 1*3*1*3
		# wrong access_token & right refresh token set to json
		tokens = {"refresh_token" : self.right_refresh_token, "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)
		self.assertEqual(client.access_token, self.right_access_token)

	def test_w_a_w_f_json_r_f_env_set(self): # 1*3*1*1
		# wrong access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)

	def test_w_a_w_f_json_w_f_env_set(self): # 1*3*1*1
		# wrong access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## wrong refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

	def test_w_a_w_f_json_n_f_env_set(self): # 1*3*1*1
		# wrong access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## no refresh token set to env
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

	def test_w_a_n_f_json_r_f_env_set(self): # 1*3*1*1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)

	def test_w_a_n_f_json_w_f_env_set(self): # 1*3*1*1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## wrong refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.wrong_refresh_token
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

	def test_w_a_n_f_json_n_f_env_set(self): # 1*3*1*1
		# wrong access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : self.wrong_access_token}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## no refresh token set to env
		client = Client(self.test_endpoint)
		with self.assertRaises(NoRefreshTokenError):
			client.get_account_info()

	def test_right_access_token_env_set(self): # 1*1*3*3
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.right_access_token
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)

	def test_n_a_r_f_json_set(self): # 1*2*1*3
		# no access_token & right refresh token set to json
		tokens = {"refresh_token" : self.right_refresh_token, "access_token" : ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)
		self.assertEqual(client.access_token, self.right_access_token)

	def test_n_a_w_f_json_r_f_env(self): # 1*2*1*1
		# no access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)

	def test_n_a_w_f_json_w_f_env(self): # 1*2*1*1
		# no access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : ""}
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

	def test_n_a_w_f_json_n_f_env(self): # 1*2*1*1
		# no access_token & wrong refresh token set to json
		tokens = {"refresh_token" : self.wrong_refresh_token, "access_token" : ""}
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

	def test_n_a_n_f_json_r_f_env(self): # 1*2*1*1
		# no access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : ""}
		with open(TOKEN_FILE, "w") as f:
			json.dump(tokens, f)
		## right refresh token set to env
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		client = Client(self.test_endpoint)
		self.assertEqual(client.get_account_info(), self.test_account_info)

	def test_n_a_n_f_json_w_f_env(self): # 1*2*1*1
		# no access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : ""}
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

	def test_n_a_n_f_json_n_f_env(self): # 1*2*1*1
		# no access_token & no refresh token set to json
		tokens = {"refresh_token" : "", "access_token" : ""}
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
            requests.get, self.test_endpoint + '/v1/me', headers={"Authorization" : 'Bearer ' + self.right_access_token}
        )
		client._check_http_error(request=request)

	def test_http_request_fail(self):
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

		client = Client(self.test_endpoint)
		request = partial(
            requests.get, self.test_endpoint + '/v1/me', headers={"Authorization" : ""}
        )
		with self.assertRaises(UnauthorizedError):
			client._check_http_error(request=request, update_tokens=False)

	def test_http_request_success_with_retry(self):
		os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"] = self.right_refresh_token
		os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"] = self.wrong_access_token

		client = Client(self.test_endpoint)
		request = partial(
            requests.get, self.test_endpoint + '/v1/me', headers=client.headers
		)
		self.assertEqual(client._check_http_error(request=request), self.test_account_info)
