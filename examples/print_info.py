"""Emo Platform API python example Getting information not specific to room.
"""

from emo_platform import Client

client = Client()

def main():
    get_account_info()
    get_rooms_list()
    get_rooms_id()
    get_stamps_list()
    get_motions_list()
    # delete_account_info() # After executing this method, you need to login web page to revive account.


def get_account_info():
    print("\n" + "=" * 20 + " account info " + "=" * 20)
    account_info = client.get_account_info()
    print("name:", account_info.name)
    print("email:", account_info.email)
    print("profile_image:", account_info.profile_image)
    print("uuid:", account_info.uuid)
    print("plan:", account_info.plan)


def delete_account_info():
    print("\n" + "=" * 20 + " delete account info " + "=" * 20)
    account_info = client.delete_account_info()
    print("name:", account_info.name)
    print("email:", account_info.email)
    print("profile_image:", account_info.profile_image)
    print("uuid:", account_info.uuid)
    print("plan:", account_info.plan)


def get_rooms_list():
    print("\n" + "=" * 20 + " rooms list " + "=" * 20)
    rooms_list = client.get_rooms_list()
    room = rooms_list.rooms[0]
    print("uuid:", room.uuid)
    print("name:", room.name)
    print("room_type:", room.room_type)
    print("room_member:", room.room_members[0])


def get_rooms_id():
    print("\n" + "=" * 20 + " rooms id " + "=" * 20)
    rooms_id = client.get_rooms_id()
    print("rooms_id:", rooms_id)


def get_stamps_list():
    print("\n" + "=" * 20 + " stamps list " + "=" * 20)
    stamps_list = client.get_stamps_list()
    stamps = stamps_list.stamps
    print("all stamps info:", stamps)
    print("motion0 uuid:", stamps[0].uuid)
    print("motion0 name:", stamps[0].name)
    print("stamp0 summary:", stamps[0].summary)
    print("stamp0 image:", stamps[0].image)


def get_motions_list():
    print("\n" + "=" * 20 + " motions list " + "=" * 20)
    motions_list = client.get_motions_list()
    motions = motions_list.motions
    print("all motions info:", motions)
    print("motion0 uuid:", motions[0].uuid)
    print("motion0 name:", motions[0].name)


if __name__ == "__main__":
    main()
