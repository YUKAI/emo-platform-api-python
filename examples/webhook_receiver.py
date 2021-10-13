"""Emo Platform API python example Receiving webhook data.
"""

import time
from threading import Thread

from emo_platform import Client, WebHook

client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))


@client.event("message.received")
def message_callback(body):
    print("body:", body)
    print("data:", body.data)


@client.event("illuminance.changed")
def illuminance_callback(body):
    print("body:", body)
    print("data:", body.data)

client.start_webhook_event()
