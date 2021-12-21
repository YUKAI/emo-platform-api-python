"""Emo Platform API python example Receiving webhook data.
"""

from emo_platform import Client, WebHook, BizAdvancedClient

# personal version
client = Client()

# business advanced version
# api_key = "YOUR API KEY" # Please replace "YOUR API KEY" with your api key to use biz version
# client = BizAdvancedClient(api_key=api_key)

# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
webhook_url = "YOUR WEBHOOK URL"
client.create_webhook_setting(WebHook(webhook_url))


@client.event("message.received")
def message_callback(body):
    print("body:", body)
    print("data:", body.data)


@client.event("illuminance.changed")
def illuminance_callback(body):
    print("body:", body)
    print("data:", body.data)


client.start_webhook_event()
