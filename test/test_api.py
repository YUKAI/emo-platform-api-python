import sys
import os
sys.path.append(os.path.abspath(".."))

import time
import unittest
from emo_platform import api


class TestGetTokens(unittest.TestCase):

	def test_get_access_token(self):
		client = api.Client()
		print(client.get_account_info())


class TestClient(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = api.Client()

	def test_get_account_info(self):
		print("\n" + "="*20 + " account info " + "="*20)
		print(self.client.get_account_info())

	@unittest.skip("delete account info")
	def test_delete_account_info(self):
		print("\n" + "="*20 + " delete account info " + "="*20)
		print(self.client.delete_account_info())

	def test_get_rooms_list(self):
		print("\n" + "="*20 + " rooms list " + "="*20)
		print(self.client.get_rooms_list())

	def test_get_rooms_id(self):
		print("\n" + "="*20 + " rooms id " + "="*20)
		print(self.client.get_rooms_id())

	def test_get_stamps_list(self):
		print("\n" + "="*20 + " stamps list " + "="*20)
		print(self.client.get_stamps_list())

	def test_get_motions_list(self):
		print("\n" + "="*20 + " motions list " + "="*20)
		print(self.client.get_motions_list())

	def test_webhook(self):
		print("\n" + "="*20 + " create webhook setting " + "="*20)
		print(self.client.create_webhook_setting(api.WebHook("new", "https://8d23-118-238-204-180.ngrok.io")))

		print("\n" + "="*20 + " create webhook setting " + "="*20)
		print(self.client.create_webhook_setting(api.WebHook("new2", "https://7d23-118-238-204-180.ngrok.io")))

		print("\n" + "="*20 + " get webhook setting " + "="*20)
		print(self.client.get_webhook_setting())

		print("\n" + "="*20 + " change webhook setting " + "="*20)
		print(self.client.change_webhook_setting(api.WebHook("update", "https://7d23-118-238-204-180.ngrok.io")))

		print("\n" + "="*20 + " get webhook setting " + "="*20)
		print(self.client.get_webhook_setting())

		print("\n" + "="*20 + " delete webhook setting " + "="*20)
		print(self.client.delete_webhook_setting())

		print("\n" + "="*20 + " get webhook setting " + "="*20)
		print(self.client.get_webhook_setting())

class TestRoomPrintInfo(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = api.Client()
		rooms_id_list = cls.client.get_rooms_id()
		cls.room = cls.client.create_room_client(rooms_id_list[0])

	def test_get_msgs(self):
		print("\n" + "="*20 + " room msgs " + "="*20)
		print(self.room.get_msgs())

	def test_get_sensors_list(self):
		print("\n" + "="*20 + " room sensors list " + "="*20)
		print(self.room.get_sensors_list())

	def test_get_sensor_values(self):
		print("\n" + "="*20 + " room sensor values " + "="*20)
		sensor_list = self.room.get_sensors_list()
		print(self.room.get_sensor_values(sensor_list['sensors'][0]['uuid']))

	def test_get_emo_settings(self):
		print("\n" + "="*20 + " room emo settings " + "="*20)
		print(self.room.get_emo_settings())

class TestRoomSendData(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = api.Client()
		rooms_id_list = cls.client.get_rooms_id()
		cls.room = cls.client.create_room_client(rooms_id_list[0])

	def test_send_audio_msg(self):
		print("\n" + "="*20 + " room send audio msg " + "="*20)
		audio_data_path = "../assets/sample_audio.mp3"
		print(self.room.send_audio_msg(audio_data_path))

	def test_send_image(self):
		print("\n" + "="*20 + " room send image " + "="*20)
		image_data_path = "../assets/sample_image.jpg"
		print(self.room.send_image(image_data_path))

	# @unittest.skip("")
	def test_send_msg(self):
		print("\n" + "="*20 + " room send msg " + "="*20)
		print(self.room.send_msg("お"*1))

	# @unittest.skip("")
	def test_send_stamp(self):
		print("\n" + "="*20 + " room send all stamps " + "="*20)
		stamp_list = self.client.get_stamps_list()
		for stamp in stamp_list['stamps']:
			time.sleep(7) # for avoiding rate limit
			print("\n" + "="*10 + " room send stamp " + "="*10)
			print(self.room.send_stamp(stamp['uuid']))
			break

	# @unittest.skip("")
	def test_send_original_motion(self):
		print("\n" + "="*20 + " room send original motion " + "="*20)
		audio_data_path = "../assets/sample_motion.json"
		print(self.room.send_original_motion(audio_data_path))

	# @unittest.skip("")
	def test_change_led_color(self):
		print("\n" + "="*20 + " room change led color " + "="*20)
		print(self.room.change_led_color(api.Color(0, 100, 100)))

	# @unittest.skip("")
	def test_move_to(self):
		print("\n" + "="*20 + " room move to " + "="*20)
		print(self.room.move_to(api.Head(40, 20)))

	# @unittest.skip("")
	def test_send_motion(self):
		print("\n" + "="*20 + " room send all motions " + "="*20)
		motion_list = self.client.get_motions_list()
		for motion in motion_list['motions']:
			time.sleep(7) # for avoiding rate limit
			print("\n" + "="*10 + " room send motion " + "="*10)
			print(self.room.send_motion(motion['uuid']))

class TestWebHookCallback(unittest.TestCase):

	def test_get_access_token(self):
		client = api.Client()
		client.change_webhook_setting(api.WebHook("test", "http://2f0e-118-238-204-180.ngrok.io"))

		@client.event('message.received')
		def message_callback(body):
			print(body)
			while(True):
				print(body.uuid)
				time.sleep(5)

		@client.event('radar.detected')
		def radar_callback(body):
			print(body)

		from threading import Thread
		thread = Thread(target=client.start_webhook_event)
		thread.start()
		while True:
			time.sleep(0.1)