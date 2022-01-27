"""Emo Platform API python example Receiving webhook data.
"""

import http.server
import json

from emo_platform import Client, EmoPlatformError, WebHook

client = Client()
# Please replace "YOUR WEBHOOK URL" with the URL forwarded to http://localhost:8000
client.create_webhook_setting(WebHook("YOUR WEBHOOK URL"))


@client.event("message.received")
def message_callback(data):
    print("message received")
    print(data)


@client.event("illuminance.changed")
def illuminance_callback(data):
    print("illuminance changed")
    print(data)


secret_key = client.start_webhook_event()


# localserver
class Handler(http.server.BaseHTTPRequestHandler):
    def _send_status(self, status):
        self.send_response(status)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()

    def do_POST(self):
        # check secret_key
        if not secret_key == self.headers["X-Platform-Api-Secret"]:
            self._send_status(401)
            return

        content_len = int(self.headers["content-length"])
        request_body = json.loads(self.rfile.read(content_len).decode("utf-8"))

        try:
            cb_func, emo_webhook_body = client.get_cb_func(request_body)
        except EmoPlatformError:
            self._send_status(501)
        cb_func(emo_webhook_body)

        self._send_status(200)


with http.server.HTTPServer(("", 8000), Handler) as httpd:
    httpd.serve_forever()
