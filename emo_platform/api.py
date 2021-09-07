import requests
import json
import time
import os
from functools import partial
from threading import Thread
from flask import Flask, request, abort
from emo_platform.exceptions import http_error_handler, NoRoomError, NoRefreshTokenError, UnauthorizedError
app = Flask(__name__)

@ app.route("/", methods=['POST'])
def emo_callback():  # emoからのwebhookを受信した際の処理
	if request.method == 'POST':
		global event_data
		event_data = request.json
		print(json.dumps(event_data, indent=2))
		return 'success', 200
	else:
		abort(400)

class Color:
	def __init__(self, red, green, blue):
		self.red = red
		self.green = green
		self.blue = blue

class Head:
	def __init__(self, angle, vertical_angle):
		self.angle = angle
		self.vertical_angle = vertical_angle

class WebHook:
	def __init__(self, description, url):
		self.description = description
		self.url = url

class PostContentType:
	APPLICATION_JSON = 'application/json'
	MULTIPART_FORMDATA = None

class Client:
	BASE_URL = "https://platform-api.bocco.me"
	TOKEN_FILE = "../key/emo-platform-api.json"

	def __init__(self):
		self.headers = {'accept':'*/*', 'Content-Type':PostContentType.APPLICATION_JSON}
		with open(self.TOKEN_FILE) as f:
			tokens = json.load(f)
		access_token = tokens['access_token']

		if access_token == "":
			try:
				access_token = os.environ["EMO_PLATFORM_API_ACCESS_TOKEN"]
			except KeyError:
				self.update_tokens()
		else :
			self.access_token = access_token
		self.headers['Authorization'] = 'Bearer ' + self.access_token

	def update_tokens(self):
		with open(self.TOKEN_FILE, "r") as f:
			tokens = json.load(f)
		refresh_token = tokens['refresh_token']

		if refresh_token != "":
			try:
				refresh_token, self.access_token = self.get_access_token(refresh_token)
				self.headers['Authorization'] = 'Bearer ' + self.access_token
				tokens['refresh_token'] = refresh_token
				tokens['access_token'] = self.access_token
				with open(self.TOKEN_FILE, "w") as f:
					json.dump(tokens, f)
			except UnauthorizedError:
				tokens['refresh_token'] = ""
				tokens['access_token'] = ""
				with open(self.TOKEN_FILE, "w") as f:
					json.dump(tokens, f)
				refresh_token = ""

		if refresh_token == "":
			try:
				refresh_token = os.environ["EMO_PLATFORM_API_REFRESH_TOKEN"]
			except KeyError:
				raise NoRefreshTokenError("Please set refresh_token as environment variable")

			try:
				refresh_token, self.access_token = self.get_access_token(refresh_token)
				self.headers['Authorization'] = 'Bearer ' + self.access_token
				tokens['refresh_token'] = refresh_token
				tokens['access_token'] = self.access_token
				with open(self.TOKEN_FILE, "w") as f:
					json.dump(tokens, f)
			except UnauthorizedError:
				raise NoRefreshTokenError("Please set new refresh_token as environment variable 'EMO_PLATFORM_API_REFRESH_TOKEN'")

	def _check_http_error(self, request, update_tokens=True):
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

	def _get(self, path, params = {}):
		request = partial(
			requests.get,
			self.BASE_URL + path,
			params=params,
			headers=self.headers
		)
		return self._check_http_error(request)

	def _post(self, path, data = {}, files = None, content_type = PostContentType.APPLICATION_JSON, update_tokens=True):
		self.headers['Content-Type'] = content_type
		request = partial(
			requests.post,
			self.BASE_URL + path,
			data=data,
			files = files,
			headers=self.headers
		)
		return self._check_http_error(request, update_tokens=update_tokens)

	def _put(self, path, data = {}):
		request = partial(
			requests.put,
			self.BASE_URL + path,
			data=data,
			headers=self.headers
		)
		return self._check_http_error(request)

	def _delete(self, path):
		request = partial(
			requests.delete,
			self.BASE_URL + path,
			headers=self.headers
		)
		return self._check_http_error(request)

	def get_access_token(self, refresh_token):
		payload = {'refresh_token' : refresh_token}
		result = self._post('/oauth/token/refresh', json.dumps(payload), update_tokens=False)
		return result["refresh_token"], result["access_token"]

	def get_account_info(self):
		return self._get('/v1/me')

	def delete_account_info(self):
		return self._delete('/v1/me')

	def get_rooms_list(self):
		return self._get('/v1/rooms')

	def get_rooms_id(self):
		result = self._get('/v1/rooms')
		try:
			room_number = len(result['rooms'])
		except KeyError:
			raise NoRoomError("Get no room id.")
		return [result['rooms'][i]['uuid'] for i in range(room_number)]

	def create_room_client(self, room_id):
		return Room(self, room_id)

	def get_stamps_list(self):
		return self._get('/v1/stamps')

	def get_motions_list(self):
		return self._get('/v1/motions')

	def get_webhook_setting(self):
		return self._get('/v1/webhook')

	def change_webhook_setting(self, webhook):
		payload = {'description': webhook.description, 'url' : webhook.url}
		return self._put('/v1/webhook', json.dumps(payload))

	def register_webhook_event(self, events):
		payload = {'events' : events}
		return self._put('/v1/webhook/events', json.dumps(payload))

	def create_webhook_setting(self, webhook):
		payload = {'description': webhook.description, 'url' : webhook.url}
		return self._post('/v1/webhook', json.dumps(payload))

	def delete_webhook_setting(self):
		return self._delete('/v1/webhook')

class Room:
	def __init__(self, base_client, room_id):
		self.base_client = base_client
		self.room_id = room_id

	def get_msgs(self, ts = None):
		params = {'before': ts} if ts else {}
		return self.base_client._get('/v1/rooms/' + self.room_id + '/messages', params=params)

	def get_sensors_list(self):
		return self.base_client._get('/v1/rooms/' + self.room_id + '/sensors')

	def get_sensor_values(self, sensor_id):
		return self.base_client._get('/v1/rooms/' + self.room_id + '/sensors/' + sensor_id + '/values')

	def send_audio_msg(self, audio_data_path):
		with open(audio_data_path, 'rb') as audio_data:
			files = {'audio' : audio_data}
			return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/audio', files=files, content_type=PostContentType.MULTIPART_FORMDATA)

	def send_image(self, image_data_path):
		with open(image_data_path, 'rb') as image_data:
			files = {'image' : image_data}
			return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/image', files=files, content_type=PostContentType.MULTIPART_FORMDATA)

	def send_msg(self, msg):
		payload = {'text' : msg}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/text', json.dumps(payload))

	def send_stamp(self, stamp_id, msg=None):
		payload = {'uuid' : stamp_id}
		if msg:
			payload['text'] = msg
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/stamp', json.dumps(payload))

	def send_original_motion(self, file_path):
		with open(file_path) as f:
			payload = json.load(f)
			return self.base_client._post('/v1/rooms/' + self.room_id + '/motions', json.dumps(payload))

	def change_led_color(self, color):
		payload = {'red' : color.red, 'green' : color.green, 'blue' : color.blue}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/motions/led_color', json.dumps(payload))

	def move_to(self, head):
		payload = {'angle' : head.angle, 'vertical_angle' : head.vertical_angle}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/motions/move_to', json.dumps(payload))

	def send_motion(self, motion_id):
		payload = {'uuid': motion_id}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/motions/preset', json.dumps(payload))

	def get_emo_settings(self):
		return self.base_client._get('/v1/rooms/' + self.room_id + '/emo/settings')

# # client.register_webhook('https://8d23-118-238-204-180.ngrok.io')
# # client.get_webhook_setting()
# # # client.register_webhook("https://webhook.site/6d557ad5-862b-4bef-897c-5129c12f2379")
# # client.register_webhook_event(["radar.detected"])

# # thread = Thread(target=app.run)
# # thread.start()
# # while True:
# # 	time.sleep(0.1)
# # app.run(host="localhost", port=3000)