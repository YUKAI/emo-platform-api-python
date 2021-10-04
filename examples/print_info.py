from emo_platform import Client

client = Client()


def main():
    pass
    get_account_info()
    get_rooms_list()
    get_rooms_id()
    get_stamps_list()
    get_motions_list()
    # delete_account_info() ## After executing this method, you need to login web page to revive account.


def get_account_info():
    print("\n" + "=" * 20 + " account info " + "=" * 20)
    print(client.get_account_info())


def delete_account_info():
    print("\n" + "=" * 20 + " delete account info " + "=" * 20)
    print(client.delete_account_info())


def get_rooms_list():
    print("\n" + "=" * 20 + " rooms list " + "=" * 20)
    print(client.get_rooms_list())


def get_rooms_id():
    print("\n" + "=" * 20 + " rooms id " + "=" * 20)
    print(client.get_rooms_id())


def get_stamps_list():
    print("\n" + "=" * 20 + " stamps list " + "=" * 20)
    print(client.get_stamps_list())


def get_motions_list():
    print("\n" + "=" * 20 + " motions list " + "=" * 20)
    print(client.get_motions_list())


if __name__ == "__main__":
    main()
