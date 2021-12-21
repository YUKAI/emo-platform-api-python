from emo_platform import BizBasicClient, BizAdvancedClient
from emo_platform.models import AccountInfo, BroadcastMsg

# Your api key to use biz version
api_key = ""

client = BizBasicClient(api_key=api_key)
# client = BizAdvancedClient(api_key=api_key)

def main():
	get_account_info()

	delete_account_info()

	account_info = AccountInfo(
		name = "ユカイ太郎",
		name_furigana = "ゆかいたろう",
		organization_name = "ユカイ工学株式会社",
		organization_unit_name = "ソフトウェア事業部",
		phone_number = "01200001111"
	)
	change_account_info(account_info)

	broadcast_msg = BroadcastMsg(
		title = "テスト",
		text = "テスト",
		executed_at = 1819300000,
		immediate = True
	)
	create_broadcast_msg(broadcast_msg)

	get_broadcast_msgs()


def get_account_info():
	print("\n" + "=" * 20 + " get account info " + "=" * 20)
	account_info = client.get_account_info()
	print("account_id:", account_info.account_id)
	print("name:", account_info.name)
	print("name_furigana:", account_info.name_furigana)
	print("email:", account_info.email)
	print("organization_name:", account_info.organization_name)
	print("organization_unit_name:", account_info.organization_unit_name)
	print("phone_number:", account_info.phone_number)
	print("plan:", account_info.plan)

def delete_account_info():
	try:
		client.delete_account_info()
	except Exception as e:
		print("\n" + "=" * 20 + " delete account info " + "=" * 20)
		print(e)

def change_account_info(account_info):
	print("\n" + "=" * 20 + " change account info " + "=" * 20)
	account_info = client.change_account_info(account_info)
	print("account_id:", account_info.account_id)
	print("name:", account_info.name)
	print("name_furigana:", account_info.name_furigana)
	print("email:", account_info.email)
	print("organization_name:", account_info.organization_name)
	print("organization_unit_name:", account_info.organization_unit_name)
	print("phone_number:", account_info.phone_number)
	print("plan:", account_info.plan)

def create_broadcast_msg(broadcast_msg):
	print("\n" + "=" * 20 + " create broadcast message" + "=" * 20)
	broadcast_msg = client.create_broadcast_msg(broadcast_msg)
	print("id: ", broadcast_msg.id)
	print("title: ", broadcast_msg.title)
	print("text: ", broadcast_msg.text)
	print("executed_at: ", broadcast_msg.executed_at)
	print("finished: ", broadcast_msg.finished)

def get_broadcast_msgs():
	print("\n" + "=" * 20 + " get broadcast msgs list " + "=" * 20)
	broadcast_msgs_list = client.get_broadcast_msgs_list()
	print("listing: ", broadcast_msgs_list.listing)
	print("messages: ", broadcast_msgs_list.messages)
	if len(broadcast_msgs_list.messages) != 0:
		message_id = broadcast_msgs_list.messages[0].id
		print("\n" + "=" * 20 + " get broadcast msg detail " + "=" * 20)
		broadcast_msg = client.get_broadcast_msg_details(message_id)
		print("messages: ", broadcast_msg.message)
		print("details: ", broadcast_msg.details)


if __name__ == "__main__":
	main()
