from fire import Fire
from typing import Optional

import emo_platform
from emo_platform.models import Tokens, WebHook, Color, Head, AccountInfo, BroadcastMsg
from emo_platform.response import EmoWebhookInfo, EmoBizAccountInfo, EmoBroadcastMessage


class Room(emo_platform.api.Room):

	def change_led_color(self, red: int=0, green: int=0, blue: int=0):
		color = Color(red, green, blue)
		super().change_led_color(color)

	def move_to(self, angle: float=0, vertical_angle: float=0):
		head_angle = Head(angle, vertical_angle)
		super().move_to(head_angle)

class Client(emo_platform.Client):

	def __init__(self, refresh_token: Optional[str]=None):
		if refresh_token is None:
			super().__init__()
		else:
			super().__init__(tokens=Tokens(refresh_token=refresh_token))

	def create_room_client(self, room_id: str):
		return Room(self, room_id)

	def room(self):
		"""部屋固有の各種apiを呼び出すclientの作成(部屋のidの自動取得を行う)
		"""
		room_id = self.get_rooms_id()[0]
		return Room(self, room_id)

	def change_webhook_setting(self, url: str, description: str="") -> EmoWebhookInfo:
		webhook = WebHook(url, description)
		return super().change_webhook_setting(webhook)

	def create_webhook_setting(self, url: str, description: str="") -> EmoWebhookInfo:
		webhook = WebHook(url, description)
		return super().create_webhook_setting(webhook)

class BizBasicRoom(emo_platform.api.BizBasicRoom):

	def change_led_color(self, red: int=0, green: int=0, blue: int=0):
		color = Color(red, green, blue)
		super().change_led_color(color)

	def move_to(self, angle: float=0, vertical_angle: float=0):
		head_angle = Head(angle, vertical_angle)
		super().move_to(head_angle)

class BizBasicClient(emo_platform.BizBasicClient):
	def __init__(self, api_key, refresh_token: Optional[str]=None):
		if refresh_token is None:
			super().__init__(api_key=api_key)
		else:
			super().__init__(api_key=api_key, tokens=Tokens(refresh_token=refresh_token))

	def create_room_client(self, room_id: str):
		return BizBasicRoom(self, room_id)

	def room(self):
		"""部屋固有の各種apiを呼び出すclientの作成(部屋のidの自動取得を行う)
		"""
		room_id = self.get_rooms_id()[0]
		return Room(self, room_id)

	def change_webhook_setting(self, url, description="") -> EmoWebhookInfo:
		webhook = WebHook(url, description)
		return super().change_webhook_setting(webhook)

	def create_webhook_setting(self, url, description="") -> EmoWebhookInfo:
		webhook = WebHook(url, description)
		return super().create_webhook_setting(webhook)

	def change_account_info(self, name, name_furigana, organization_name, organization_unit_name, phone_number) -> EmoBizAccountInfo:
		account_info = AccountInfo(name, name_furigana, organization_name, organization_name, organization_unit_name, phone_number)
		return super().change_account_info(account_info)

	def create_broadcast_msg(self, title, text, executed_at, immediate) -> EmoBroadcastMessage:
		broadcast_msg = EmoBroadcastMessage(title, text, executed_at, immediate)
		return super().create_broadcast_msg(broadcast_msg)

class BizAdvancedRoom(emo_platform.api.BizAdvancedRoom):

	def change_led_color(self, red: int=0, green: int=0, blue: int=0):
		color = Color(red, green, blue)
		super().change_led_color(color)

	def move_to(self, angle: float=0, vertical_angle: float=0):
		head_angle = Head(angle, vertical_angle)
		super().move_to(head_angle)

class BizAdvancedClient(emo_platform.BizAdvancedClient):
	def __init__(self, api_key, refresh_token=None):
		if refresh_token is None:
			super().__init__(api_key=api_key)
		else:
			super().__init__(api_key=api_key, tokens=Tokens(refresh_token=refresh_token))

	def create_room_client(self, room_id: str):
		return BizAdvancedRoom(self, room_id)

	def room(self):
		"""部屋固有の各種apiを呼び出すclientの作成(部屋のidの自動取得を行う)
		"""
		room_id = self.get_rooms_id()[0]
		return Room(self, room_id)

	def change_webhook_setting(self, url, description="") -> EmoWebhookInfo:
		webhook = WebHook(url, description)
		return super().change_webhook_setting(webhook)

	def create_webhook_setting(self, url, description="") -> EmoWebhookInfo:
		webhook = WebHook(url, description)
		return super().create_webhook_setting(webhook)

	def change_account_info(self, name, name_furigana, organization_name, organization_unit_name, phone_number) -> EmoBizAccountInfo:
		account_info = AccountInfo(name, name_furigana, organization_name, organization_name, organization_unit_name, phone_number)
		return super().change_account_info(account_info)

	def create_broadcast_msg(self, title, text, executed_at, immediate) -> EmoBroadcastMessage:
		broadcast_msg = EmoBroadcastMessage(title, text, executed_at, immediate)
		return super().create_broadcast_msg(broadcast_msg)

class Command:
	personal = Client
	biz_basic = BizBasicClient
	biz_advanced  = BizAdvancedClient

Fire(Command)