import asyncio

from emo_platform import AsyncClient


async def main():
    # await client.set_tokens()
    client = await AsyncClient()
    await get_account_info(client)
    await get_rooms_list(client)
    await get_rooms_id(client)
    await get_stamps_list(client)
    await get_motions_list(client)
    # await delete_account_info(client) ## After executing this method, you need to login web page to revive account.


async def get_account_info(client):
    print("\n" + "=" * 20 + " account info " + "=" * 20)
    print(await client.get_account_info())


async def delete_account_info(client):
    print("\n" + "=" * 20 + " delete account info " + "=" * 20)
    print(await client.delete_account_info())


async def get_rooms_list(client):
    print("\n" + "=" * 20 + " rooms list " + "=" * 20)
    print(await client.get_rooms_list())


async def get_rooms_id(client):
    print("\n" + "=" * 20 + " rooms id " + "=" * 20)
    print(await client.get_rooms_id())


async def get_stamps_list(client):
    print("\n" + "=" * 20 + " stamps list " + "=" * 20)
    print(await client.get_stamps_list())


async def get_motions_list(client):
    print("\n" + "=" * 20 + " motions list " + "=" * 20)
    print(await client.get_motions_list())


if __name__ == "__main__":
    asyncio.run(main())
