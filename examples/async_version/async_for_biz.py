import asyncio

from emo_platform import BizBasicAsyncClient, BizAdvancedAsyncClient
from emo_platform.models import AccountInfo, BroadcastMsg

# Please replace "YOUR API KEY" with your api key to use biz version
api_key = "YOUR API KEY"

# business basic version
client = BizBasicAsyncClient(api_key=api_key)

# business advanced version
# client = BizAdvancedAsyncClient(api_key=api_key)

async def main():
	await get_account_info()

	await delete_account_info()

	account_info = AccountInfo(
		name = "ユカイ太郎",
		name_furigana = "ゆかいたろう",
		organization_name = "ユカイ工学株式会社",
		organization_unit_name = "ソフトウェア事業部",
		phone_number = "01200001111"
	)
	await change_account_info(account_info)

	broadcast_msg = BroadcastMsg(
		title = "テスト",
		text = "テスト",
		executed_at = 1819300000,
		immediate = True
	)
	await create_broadcast_msg(broadcast_msg)

	await get_broadcast_msgs()


async def get_account_info():
	print("\n" + "=" * 20 + " get account info " + "=" * 20)
	account_info = await client.get_account_info()
	print("account_id:", account_info.account_id)
	print("name:", account_info.name)
	print("name_furigana:", account_info.name_furigana)
	print("email:", account_info.email)
	print("organization_name:", account_info.organization_name)
	print("organization_unit_name:", account_info.organization_unit_name)
	print("phone_number:", account_info.phone_number)
	print("plan:", account_info.plan)

async def delete_account_info():
	try:
		await client.delete_account_info()
	except Exception as e:
		print("\n" + "=" * 20 + " delete account info " + "=" * 20)
		print(e)

async def change_account_info(account_info):
	print("\n" + "=" * 20 + " change account info " + "=" * 20)
	account_info = await client.change_account_info(account_info)
	print("account_id:", account_info.account_id)
	print("name:", account_info.name)
	print("name_furigana:", account_info.name_furigana)
	print("email:", account_info.email)
	print("organization_name:", account_info.organization_name)
	print("organization_unit_name:", account_info.organization_unit_name)
	print("phone_number:", account_info.phone_number)
	print("plan:", account_info.plan)

async def create_broadcast_msg(broadcast_msg):
	print("\n" + "=" * 20 + " create broadcast message" + "=" * 20)
	broadcast_msg = await client.create_broadcast_msg(broadcast_msg)
	print("id: ", broadcast_msg.id)
	print("title: ", broadcast_msg.title)
	print("text: ", broadcast_msg.text)
	print("executed_at: ", broadcast_msg.executed_at)
	print("finished: ", broadcast_msg.finished)

async def get_broadcast_msgs():
	print("\n" + "=" * 20 + " get broadcast msgs list " + "=" * 20)
	broadcast_msgs_list = await client.get_broadcast_msgs_list()
	print("listing: ", broadcast_msgs_list.listing)
	print("messages: ", broadcast_msgs_list.messages)
	if len(broadcast_msgs_list.messages) != 0:
		message_id = broadcast_msgs_list.messages[0].id
		print("\n" + "=" * 20 + " get broadcast msg detail " + "=" * 20)
		broadcast_msg = await client.get_broadcast_msg_details(message_id)
		print("messages: ", broadcast_msg.message)
		print("details: ", broadcast_msg.details)


if __name__ == "__main__":
    asyncio.run(main())
