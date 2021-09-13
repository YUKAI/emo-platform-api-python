import asyncio

from emo_platform import AsyncClient, WebHook


client = None

async def main():
    global client
    client = await AsyncClient()
    webhook = WebHook("http://localhost:8000", "test")
    events = ["message.received"]
    await create_webhook_setting(webhook)
    await get_webhook_setting()
    await register_webhook_event(events)
    await get_webhook_setting()
    await delete_webhook_setting()


async def create_webhook_setting(webhook):
    print("\n" + "=" * 20 + " create webhook setting " + "=" * 20)
    print(await client.create_webhook_setting(webhook))


async def get_webhook_setting():
    print("\n" + "=" * 20 + " get webhook setting " + "=" * 20)
    print(await client.get_webhook_setting())


async def register_webhook_event(events):
    print("\n" + "=" * 20 + " register webhook event " + "=" * 20)
    print(await client.register_webhook_event(events))


async def delete_webhook_setting():
    print("\n" + "=" * 20 + " delete webhook setting " + "=" * 20)
    print(await client.delete_webhook_setting())


if __name__ == "__main__":
    asyncio.run(main())
