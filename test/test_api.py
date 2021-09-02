import sys
import os
sys.path.append(os.path.abspath(".."))

import time
import unittest
from emo_platform import api

class TestClientPrintInfo(unittest.TestCase):

	def setUp(self):
		refresh_token = "cd86f829-ebdd-4c74-aaad-7c7cb8896cfb"
		self.client = api.Client(refresh_token)

	def test_get_account_info(self):
		print("\n" + "="*20 + " account info " + "="*20)
		print(self.client.get_account_info())

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

	def test_get_webhook_setting(self):
		print("\n" + "="*20 + " webhook setting " + "="*20)
		print(self.client.get_webhook_setting())

class TestRoomPrintInfo(unittest.TestCase):

	def setUp(self):
		refresh_token = "1686113e-8bcf-4c1b-acbf-f47edc4840cc"
		client = api.Client(refresh_token)
		rooms_id_list = client.get_rooms_id()
		self.room = client.create_room_client(rooms_id_list[0])

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

	def setUp(self):
		refresh_token = "1686113e-8bcf-4c1b-acbf-f47edc4840cc"
		self.client = api.Client(refresh_token)
		rooms_id_list = self.client.get_rooms_id()
		self.room = self.client.create_room_client(rooms_id_list[0])

	# def test_send_audio_msg(self):
	# 	print("\n" + "="*20 + " room send audio msg " + "="*20)
	# 	audio_data_path = "../assets/sample_audio.mp3"
	# 	print(self.room.send_audio_msg(audio_data_path))

	def test_send_image(self):
		pass

	def test_send_msg(self):
		print("\n" + "="*20 + " room send msg " + "="*20)
		print(self.room.send_msg("おはよう"))

	def test_send_stamp(self):
		print("\n" + "="*20 + " room send all stamps " + "="*20)
		stamp_list = self.client.get_stamps_list()
		for stamp in stamp_list['stamps']:
			time.sleep(7) # for avoiding rate limit
			print("\n" + "="*10 + " room send stamp " + "="*10)
			print(self.room.send_stamp(stamp['uuid']))
