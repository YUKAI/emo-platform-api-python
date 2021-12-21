"""Emo Platform API python example Setting webhook.
"""

from emo_platform import BizAdvancedClient, Client, WebHook

# personal version
client = Client()

# business advanced version
# api_key = "YOUR API KEY" # Please replace "YOUR API KEY" with your api key to use biz version
# client = BizAdvancedClient(api_key=api_key)


def main():
    webhook = WebHook("http://localhost:8000", "test")
    events = ["message.received"]
    create_webhook_setting(webhook)
    get_webhook_setting()
    register_webhook_event(events)
    get_webhook_setting()
    delete_webhook_setting()


def create_webhook_setting(webhook):
    print("\n" + "=" * 20 + " create webhook setting " + "=" * 20)
    print(client.create_webhook_setting(webhook))


def get_webhook_setting():
    print("\n" + "=" * 20 + " get webhook setting " + "=" * 20)
    print(client.get_webhook_setting())


def register_webhook_event(events):
    print("\n" + "=" * 20 + " register webhook event " + "=" * 20)
    print(client.register_webhook_event(events))


def delete_webhook_setting():
    print("\n" + "=" * 20 + " delete webhook setting " + "=" * 20)
    print(client.delete_webhook_setting())


if __name__ == "__main__":
    main()
