import requests
import json
import time
import base64
from threading import Thread
from flask import Flask, request, abort
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

class ResStatus:
	OK = 200

class Client:
	BASE_URL = "https://platform-api.bocco.me"

	def __init__(self, refresh_token):
		self.headers = {'accept':'*/*', 'Content-Type':'application/json'}
		self.access_token, self.refresh_token = self.get_access_token(refresh_token)
		self.headers['Authorization'] = 'Bearer ' + self.access_token

	def _get(self, path, params = {}):
		result = requests.get(self.BASE_URL + path,
							params=params,
							headers=self.headers)
		return result.status_code, result.json()

	def _post(self, path, data = {}):
		result = requests.post(self.BASE_URL + path,
							data=data,
							headers=self.headers)
		return result.status_code, result.json()

	def _put(self, path, data = {}):
		result = requests.put(self.BASE_URL + path,
							data=data,
							headers=self.headers)
		return result.status_code, result.json()

	def _delete(self, path):
		result = requests.delete(self.BASE_URL + path,
							headers=self.headers)
		return result.status_code, result.json()

	def get_access_token(self, refresh_token):
		payload = {'refresh_token' : refresh_token}
		status, result = self._post('/oauth/token/refresh', json.dumps(payload))
		if status == ResStatus.OK:
			return result["access_token"], result["refresh_token"]

	def get_account_info(self):
		return self._get('/v1/me')

	def get_rooms_list(self):
		return self._get('/v1/rooms')

	def get_rooms_id(self):
		_, result = self._get('/v1/rooms')
		try:
			room_number = len(result['rooms'])
		except KeyError:
			return []
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
			# ? payload format
			payload = {'audio' : base64.b64encode(audio_data.read())}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/audio', json.dumps(payload))

	def send_image(self, image_data):
		# ? payload format
		payload = {'image' : image_data}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/image', json.dumps(payload))

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
			payload = f.read()
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages', json.dumps(payload))

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