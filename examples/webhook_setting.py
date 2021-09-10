from emo_platform import Client, WebHook

client = Client()

def main():
	webhook = WebHook("http://localhost:8000", "test")
	events = ["message.received"]
	create_webhook_setting(webhook)
	get_webhook_setting()
	register_webhook_event(events)
	get_webhook_setting()
	delete_webhook_setting()

def create_webhook_setting(webhook):
	print("\n" + "="*20 + " create webhook setting " + "="*20)
	print(client.create_webhook_setting(webhook))

def get_webhook_setting():
	print("\n" + "="*20 + " get webhook setting " + "="*20)
	print(client.get_webhook_setting())

def register_webhook_event(events):
	print("\n" + "="*20 + " register webhook event " + "="*20)
	print(client.register_webhook_event(events))

def delete_webhook_setting():
	print("\n" + "="*20 + " delete webhook setting " + "="*20)
	print(client.delete_webhook_setting())

if __name__ == "__main__":
	main()