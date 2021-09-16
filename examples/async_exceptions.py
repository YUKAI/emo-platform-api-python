import asyncio

from emo_platform import AsyncClient, BadRequestError, NotFoundError, RateLimitError


client = AsyncClient()
rooms_id_list = client.get_rooms_id()
room = client.create_room_client(rooms_id_list[0])

async def main():
    await no_webhook_setting()
    await send_over_sized_msg()
    # await over_rate_limit() ## After calling this method, wait 1 minute until rate limit released.


async def no_webhook_setting():
    try:
        await client.delete_webhook_setting()
        await client.get_webhook_setting()
    except NotFoundError as e:
        print(e)


async def send_over_sized_msg():
    try:
        await room.send_msg("あ" * 2000)
    except BadRequestError as e:
        print(e)


async def over_rate_limit():
    for i in range(10):
        try:
            await client.get_account_info()
        except RateLimitError as e:
            print(i + 1, e)


if __name__ == "__main__":
    asyncio.run(main())
