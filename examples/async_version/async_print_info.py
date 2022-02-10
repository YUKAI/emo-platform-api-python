"""Emo Platform API python example Getting information not specific to room.
"""

import asyncio

from emo_platform import AsyncClient

# personal version
client = AsyncClient()


async def main():
    await get_account_info()
    await get_rooms_list()
    await get_stamps_list()
    await get_motions_list()
    # await delete_account_info() # After executing this method, you need to login web page to revive account.


async def get_account_info():
    print("\n" + "=" * 20 + " account info " + "=" * 20)
    account_info = await client.get_account_info()
    print("name:", account_info.name)
    print("email:", account_info.email)
    print("profile_image:", account_info.profile_image)
    print("uuid:", account_info.uuid)
    print("plan:", account_info.plan)


async def delete_account_info():
    print("\n" + "=" * 20 + " delete account info " + "=" * 20)
    account_info = await client.delete_account_info()
    print("name:", account_info.name)
    print("email:", account_info.email)
    print("profile_image:", account_info.profile_image)
    print("uuid:", account_info.uuid)
    print("plan:", account_info.plan)


async def get_rooms_list():
    print("\n" + "=" * 20 + " rooms list " + "=" * 20)
    rooms_list = await client.get_rooms_list()
    room = rooms_list.rooms[0]
    print("uuid:", room.uuid)
    print("name:", room.name)
    print("room_type:", room.room_type)
    print("room_member:", room.room_members[0])


async def get_stamps_list():
    print("\n" + "=" * 20 + " stamps list " + "=" * 20)
    stamps_list = await client.get_stamps_list()
    stamps = stamps_list.stamps
    print("all stamps info:", stamps)
    print("motion0 uuid:", stamps[0].uuid)
    print("motion0 name:", stamps[0].name)
    print("stamp0 summary:", stamps[0].summary)
    print("stamp0 image:", stamps[0].image)


async def get_motions_list():
    print("\n" + "=" * 20 + " motions list " + "=" * 20)
    motions_list = await client.get_motions_list()
    motions = motions_list.motions
    print("all motions info:", motions)
    print("motion0 uuid:", motions[0].uuid)
    print("motion0 name:", motions[0].name)


if __name__ == "__main__":
    asyncio.run(main())
