import asyncio
from threading import Thread

from emo_platform import AsyncClient, WebHook

client = AsyncClient()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

async def print_queue(queue):
    while True:
        item = await queue.get()
        print(item.data)


async def main():
    queue = asyncio.Queue()

    @client.event("message.received")
    async def message_callback(body):
        await asyncio.sleep(1)
        await queue.put(body)

    task_queue = asyncio.create_task(print_queue(queue))

    await client.start_webhook_event(port=8000, tasks=[task_queue])


if __name__ == "__main__":
    asyncio.run(main())
