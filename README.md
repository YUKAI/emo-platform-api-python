# BOCCO emo platform api python sdk (β version)

## How to install
### Using poetry (if you want to use in python virtual environment)
If poetry has not been installed, please see [this page](https://python-poetry.org/docs/) to install.

```bash
# Python 3.7+ required
poetry install --no-dev
```

When you execute python code,

```bash
poetry run python your_python_code.py
```

### Using PyPl

```
# Python 3.7+ required
$ pip3 install emo-platform-api-sdk
```

## Setting api tokens

You can see access token & refresh token from dashboard in [this page](https://platform-api.bocco.me/dashboard/login) after login.

Then, set those tokens as environment variables in terminal.

```bash
export EMO_PLATFORM_API_ACCESS_TOKEN="***"
export EMO_PLATFORM_API_REFRESH_TOKEN="***"
```

Or, you can give as argument when initializing client in python code.

```python
from emo_platform import Client, Tokens

client = Client(Tokens(access_token="***", refresh_token="***"))
```

## For business user
When you use business version, you need to give api_key as argument when initializing client.

You can find the API key in [this page](https://platform-api.bocco.me/dashboard/login) after login with business account.
```python
from emo_platform import BizBasicClient, BizAdvancedClient

# business basic version
client = BizBasicClient(api_key="***")

# business advanced version
client = BizAdvancedClient(api_key="***")
```

## Usage Example

You can also see other examples in "examples" directory.

### Note
- When you initialize emo_platform.Client, two json files (emo-platform-api.json & emo-platform-api_previous.json) are created in the path where emo_platform module was installed.
	- These files are used to store the tokens information.
	- See the documentation for details.
- You can change the path where these json files are created, as shown below.

```python
import os
from emo_platform import Client

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

client = Client(token_file_path=CURRENT_DIR)
```

### Example1 : Using client
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

### Example2 : Receive webhook

In another terminal, execute ngrok and copy URL forwarded to http://localhost:8000.
```bash
ngrok http 8000
```

```python
from emo_platform import Client, WebHook

client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

@client.event('message.received')
def message_callback(data):
	print(data)

@client.event('illuminance.changed')
def illuminance_callback(data):
	print(data)

client.start_webhook_event()

```
