# BOCCO emo platform api python sdk

## Setup for developer
If poetry has not been installed, please see [this page](https://python-poetry.org/docs/) to install.

```bash
# Python 3.6+ required
poetry install --no-dev
```

When you execute python code,

```bash
poetry run python your_python_code.py
```

## Setting api tokens

You can see access token & refresh token from dashboard in [this page](https://platform-api.bocco.me/dashboard/login) after login.

Then, set those tokens as environment variables.

```bash
export EMO_PLATFORM_API_ACCESS_TOKEN="***"
export EMO_PLATFORM_API_REFRESH_TOKEN="***"
```

## Usage Example

You can also see other examples in "examples" directory.

### Using client
```python
from emo_platform import Client, Head

client = Client()

print(client.get_account_info())
print(client.get_stamps_list())

room_id_list = client.get_rooms_id()
room_client = client.create_room_client(room_id_list[0])

print(room_client.get_msgs())
room_client.move_to(Head(10,10))
```

### Receive webhook

In another terminal, execute ngrok and copy URL forwarded to http://localhost:8000.
```bash
ngrok http 8000
```

```python
from emo_platform import Client, WebHook
from threading import Thread
import time

client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

@client.event('message.received')
def message_callback(data):
	print(data)

@client.event('illuminance.changed')
def radar_callback(data):
	print(data)

thread = Thread(target=client.start_webhook_event)
thread.start()

while True:
	time.sleep(0.1)
```
