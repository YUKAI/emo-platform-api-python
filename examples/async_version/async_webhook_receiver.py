"""Emo Platform API python example Receiving webhook data.
"""

import json, asyncio
from aiohttp import web
from emo_platform import AsyncClient, WebHook, EmoPlatformError

client = AsyncClient()

async def print_queue(queue):
    while True:
        item = await queue.get()
        print("body:", item)
        print("data:", item.data)

async def main():
    # Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
    await client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

    queue = asyncio.Queue()

    @client.event("message.received")
    async def message_callback(body):
        await asyncio.sleep(1)  # Do not use time.sleep in async def
        await queue.put(body)

    secret_key = await client.start_webhook_event()

    routes = web.RouteTableDef()

    @routes.post('/')
    async def emo_webhook(request):
        if request.headers["X-Platform-Api-Secret"] == secret_key:
            body = await request.json()
            try:
                cb_func, emo_webhook_body = client.get_cb_func(body)
            except EmoPlatformError:
                return web.Response(status=501)
            asyncio.create_task(cb_func(emo_webhook_body))
            return web.Response()
        else:
            return web.Response(status=401)

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8000)
    await site.start()

    await print_queue(queue)

asyncio.run(main())
