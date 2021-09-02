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

class Client:
	BASE_URL = "https://platform-api.bocco.me"

	def __init__(self, refresh_token):
		self.headers = {'accept':'*/*', 'Content-Type':'application/json'}
		self.access_token, self.refresh_token = self.get_access_token(refresh_token)
		self.headers['Authorization'] = 'Bearer ' + self.access_token
		self.room_id = None

	def _get(self, path, params = {}):
		return requests.get(self.BASE_URL + path,
							params=params,
							headers=self.headers).json()

	def _post(self, path, data = {}):
		return requests.post(self.BASE_URL + path,
							data=data,
							headers=self.headers).json()

	def _put(self, path, data = {}):
		return requests.put(self.BASE_URL + path,
							data=data,
							headers=self.headers).json()

	def get_access_token(self, refresh_token):
		payload = {'refresh_token' : refresh_token}
		result = self._post('/oauth/token/refresh', json.dumps(payload))
		return result["access_token"], result["refresh_token"]

	def get_account_info(self):
		return self._get('/v1/me')

	def get_rooms_list(self):
		return self._get('/v1/rooms')

	def get_rooms_id(self):
		result = self._get('/v1/rooms')
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

	def register_webhook(self, url):
		payload = {'description': 'my webhook', 'url' : url}
		result = self._post('/v1/webhook', json.dumps(payload))
		print(result)

	def register_webhook_event(self, events):
		payload = {'events' : events}
		return self._put('/v1/webhook/events', json.dumps(payload))


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
			# import pdb; pdb.set_trace()
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/audio', json.dumps(payload))

	def send_image(self, image_data):
		# ? payload format
		payload = {'image' : image_data}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/image', json.dumps(payload))

	def send_msg(self, msg):
		payload = {'text' : msg}
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/text', json.dumps(payload))

	def send_stamp(self, stamp_id, msg=None):
		# ! msg size 1~20 validation
		payload = {'uuid' : stamp_id}
		if msg:
			payload['text'] = msg
		return self.base_client._post('/v1/rooms/' + self.room_id + '/messages/stamp', json.dumps(payload))

	def get_emo_settings(self):
		return self.base_client._get('/v1/rooms/' + self.room_id + '/emo/settings')

# client = Client(
# )

# rooms_id_list = client.get_rooms_id()
# room1 = client.create_room_client(rooms_id_list[0])
# # print(room1.get_room_msgs())
# room1.send_msg("おはよう")
# # print(client.get_account_info())
# # client.send_msg("ニーハオ")
# # client.register_webhook('https://8d23-118-238-204-180.ngrok.io')
# # client.get_webhook_setting()
# # # client.register_webhook("https://webhook.site/6d557ad5-862b-4bef-897c-5129c12f2379")
# # client.register_webhook_event(["radar.detected"])

# # thread = Thread(target=app.run)
# # thread.start()
# # while True:
# # 	time.sleep(0.1)
# # app.run(host="localhost", port=3000)

# # req.date()  # サーバ、クライアント間の時刻同期
# # req.webhook_url("http://"+req.getIPv4()+":5000/webhook")