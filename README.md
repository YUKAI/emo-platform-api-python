# BOCCO emo platform api python sdk

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

### Note
- Once you set tokens as arguments or environment variables, the tokens are saved in the sdk and you don't need to specify any arguments or set any environment variables next time.
- If you want to overwrite the tokens with the other tokens, for example if you want to change your account, set the new tokens again with arguments or environment variables.

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
- When you initialize emo_platform.Client, without the argument `is_server` given as `True` , two json files (emo-platform-api.json & emo-platform-api_previous.json) are created in the path where emo_platform module was installed.
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

#### Case1 : Using function `start_webhook_event()` (**Recommended**)
You can use the decorator `event` to register functions as callback functions.

And, you can get the corresponding callback function and the parsed body by giving the webhook request body as the argument of the function `get_cb_func`.

Please check if the SECRET_KEY_ID in the header of the webhook request is the same as the return value of `start_webhook_event()` to avoid unexpected requests from third parties.
```python
import json, http.server
from emo_platform import Client, WebHook, SECRET_KEY_ID


client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

@client.event('message.received')
def message_callback(data):
	print("message received")
	print(data)

@client.event('illuminance.changed')
def illuminance_callback(data):
	print("illuminance changed")
	print(data)

secret_key = client.start_webhook_event()


# localserver
class Handler(http.server.BaseHTTPRequestHandler):
	def do_POST(self):
		# check secret_key
		if not secret_key == self.headers[SECRET_KEY_ID]:
			self.send_response(401)

		content_len = int(self.headers['content-length'])
		request_body = json.loads(self.rfile.read(content_len).decode('utf-8'))

		try:
			cb_func, emo_webhook_body = client.get_cb_func(request_body)
		except emo_platform.EmoPlatformError:
			self.send_response(501)
		cb_func(emo_webhook_body)

		self.send_response(200)

with http.server.HTTPServer(('', 8000), Handler) as httpd:
	httpd.serve_forever()

```

#### Case2 : Using function `register_webhook_event()` (**Not recommended**)
You can't use the decorator `event` to register functions as callback functions.

So, you need to call the callback functions yourself after webhook request body is parsed using `parse_webhook_body`.

Please check if the SECRET_KEY_ID in the header of the webhook request is the same as the return value of `register_webhook_event()` to avoid unexpected requests from third parties.

```python
import json, http.server
from emo_platform import (
	Client, WebHook, SECRET_KEY_ID, parse_webhook_body
)


client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))

def message_callback(data):
	print("message received")
	print(data)

def illuminance_callback(data):
	print("illuminance changed")
	print(data)

secret_key = client.register_webhook_event(
	['message.received','illuminance.changed' ]
)

# localserver
class Handler(http.server.BaseHTTPRequestHandler):
	def do_POST(self):
		# check secret_key
		if not secret_key == self.headers[SECRET_KEY_ID]:
			self.send_response(401)

		content_len = int(self.headers['content-length'])
		request_body = json.loads(self.rfile.read(content_len).decode('utf-8'))

		emo_webhook_body = parse_webhook_body(request_body)
		if emo_webhook_body.event == "message.received":
			message_callback(emo_webhook_body)
		elif emo_webhook_body.event == "illuminance.changed":
			illuminance_callback(emo_webhook_body)
		else:
			pass

		self.send_response(200)

with http.server.HTTPServer(('', 8000), Handler) as httpd:
	httpd.serve_forever()

```

## Cli Tool
You can use command line interface when you install this sdk with poetry.

### Example1 : Use client
Initially, you need to specify your account refresh token.
```bash
$ poetry run python cli.py personal --refresh_token *** get_account_info
```
Once you set refresh_token, you don't need to set again.
```bash
$ poetry run python cli.py personal get_account_info
```

### Example2 : Use room client
Please replace ROOM_ID with room id which you want to use.
```
$ poetry run python cli.py personal create_room_client ROOM_ID change_led_color 10 10 200
```
You can get room id as shown below.
```
$ poetry run python cli.py personal get_rooms_id
```

Or, you can use "room" command which does not require the room id to be specified.
This is because it calls get_rooms_id() internally and specifies the first room id.
```
$ poetry run python cli.py personal room change_led_color 10 10 200
```
