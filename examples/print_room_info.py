"""Emo Platform API python example Getting information specific to room.
"""

from emo_platform import Client

client = Client()
rooms_id_list = client.get_rooms_id()
# create room client
room = client.create_room_client(rooms_id_list[0])


def main():
    get_latest_msg()
    get_sensors_list()
    get_room_sensor_info()
    get_emo_settings()


def get_latest_msg():
    print("\n" + "=" * 20 + " room msgs " + "=" * 20)
    msgs = room.get_msgs()
    msg_latest = msgs.messages[0]
    print("time stamp:", msg_latest.sequence)
    print("id:", msg_latest.unique_id)
    print("users:", msg_latest.user)
    print("message_info:", msg_latest.message)
    print("media:", msg_latest.media)

def get_sensors_list():
    print("\n" + "=" * 20 + " room sensors list " + "=" * 20)
    print(room.get_sensors_list())


def get_room_sensor_info():
    print("\n" + "=" * 20 + " room sensor values " + "=" * 20)
    sensor_list = room.get_sensors_list()
    for sensor in sensor_list.sensors:
        if(sensor.sensor_type == "room"):
            room_sensor = sensor
            room_sensor_values = room.get_sensor_values(room_sensor.uuid)
            print("type:", room_sensor_values.sensor_type)
            print("uuid:", room_sensor_values.uuid)
            print("nickname:", room_sensor_values.nickname)
            print("events:", room_sensor_values.events)

def get_emo_settings():
    print("\n" + "=" * 20 + " room emo settings " + "=" * 20)
    emo_settings = room.get_emo_settings()
    print("nickname:", emo_settings.nickname)
    print("wakeword:", emo_settings.wakeword)
    print("volume:", emo_settings.volume)
    print("voice_pitch:", emo_settings.voice_pitch)
    print("voice_speed:", emo_settings.voice_speed)
    print("lang:", emo_settings.lang)
    print("serial_number:", emo_settings.serial_number)
    print("timezone:", emo_settings.timezone)
    print("zip_code:", emo_settings.zip_code)

if __name__ == "__main__":
    main()
