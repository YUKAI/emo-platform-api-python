from emo_platform import Client

client = Client()
rooms_id_list = client.get_rooms_id()
room = client.create_room_client(rooms_id_list[0])


def main():
    get_msgs()
    get_sensors_list()
    get_sensor_values()
    get_emo_settings()


def get_msgs():
    print("\n" + "=" * 20 + " room msgs " + "=" * 20)
    print(room.get_msgs())


def get_sensors_list():
    print("\n" + "=" * 20 + " room sensors list " + "=" * 20)
    print(room.get_sensors_list())


def get_sensor_values():
    print("\n" + "=" * 20 + " room sensor values " + "=" * 20)
    sensor_list = room.get_sensors_list()
    print(room.get_sensor_values(sensor_list.sensors[0].uuid))


def get_emo_settings():
    print("\n" + "=" * 20 + " room emo settings " + "=" * 20)
    print(room.get_emo_settings())


if __name__ == "__main__":
    main()
