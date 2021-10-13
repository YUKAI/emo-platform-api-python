"""Emo Platform API python example Receiving webhook data.
"""

import asyncio
from threading import Thread

from emo_platform import AsyncClient, WebHook

client = AsyncClient()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

async def print_queue(queue):
    while True:
        item = await queue.get()
        print("body:", item)
        print("data:", item.data)


async def main():
    queue = asyncio.Queue()

    @client.event("message.received")
    async def message_callback(body):
        await asyncio.sleep(1) # Do not use time.sleep in async def
        await queue.put(body)

    # Create task you want to execute in parallel
    task_queue = asyncio.create_task(print_queue(queue))

    # Await start_webhook_event last.
    # Give task list to be executed in parallel as the argument.
    await client.start_webhook_event(port=8000, tasks=[task_queue])


if __name__ == "__main__":
    asyncio.run(main())
