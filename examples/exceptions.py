from emo_platform import BadRequestError, Client, NotFoundError, RateLimitError

client = Client()
rooms_id_list = client.get_rooms_id()
room = client.create_room_client(rooms_id_list[0])


def main():
    no_webhook_setting()
    send_over_sized_msg()
    # over_rate_limit() ## After calling this method, wait 1 minute until rate limit released.


def no_webhook_setting():
    try:
        client.delete_webhook_setting()
        client.get_webhook_setting()
    except NotFoundError as e:
        print(e)


def send_over_sized_msg():
    try:
        room.send_msg("あ" * 2000)
    except BadRequestError as e:
        print(e)


def over_rate_limit():
    for i in range(10):
        try:
            client.get_account_info()
        except RateLimitError as e:
            print(i + 1, e)


if __name__ == "__main__":
    main()
