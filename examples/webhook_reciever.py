import time
from threading import Thread

from emo_platform import Client, WebHook

client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))


@client.event("message.received")
def message_callback(body):
    print(body)
    print(body.data)


@client.event("illuminance.changed")
def radar_callback(body):
    print(body)
    print(body.data)


thread = Thread(target=client.start_webhook_event)
thread.start()

while True:
    time.sleep(0.1)
