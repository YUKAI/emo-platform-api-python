import asyncio
from threading import Thread

from emo_platform import AsyncClient, WebHook

client = AsyncClient()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))


@client.event("message.received")
async def message_callback(body):
    await asyncio.sleep(5)
    print(body)
    print(body.data)


@client.event("illuminance.changed")
async def radar_callback(body):
    print(body)
    print(body.data)


thread = Thread(target=client.start_webhook_event)
thread.start()


async def main():
    while True:
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
