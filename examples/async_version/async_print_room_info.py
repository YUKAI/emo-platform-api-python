"""Emo Platform API python example Getting information specific to room.
"""

import asyncio

from emo_platform import AsyncClient, BizAdvancedAsyncClient, BizBasicAsyncClient

# personal version
client = AsyncClient()

# business advanced version
# api_key = "YOUR API KEY" # Please replace "YOUR API KEY" with your api key to use biz version
# client = BizAdvancedAsyncClient(api_key=api_key)


async def main():
    rooms_id_list = await client.get_rooms_id()
    # create room client
    room = client.create_room_client(rooms_id_list[0])
    await get_latest_msg(room)
    await get_sensors_list(room)
    await get_sensor_values(room)
    await get_emo_settings(room)


async def get_latest_msg(room):
    print("\n" + "=" * 20 + " room msgs " + "=" * 20)
    msgs = await room.get_msgs()
    msg_latest = msgs.messages[0]
    print("time stamp:", msg_latest.sequence)
    print("id:", msg_latest.unique_id)
    print("users:", msg_latest.user)
    print("message_info:", msg_latest.message)
    print("media:", msg_latest.media)


async def get_sensors_list(room):
    print("\n" + "=" * 20 + " room sensors list " + "=" * 20)
    print(await room.get_sensors_list())


async def get_sensor_values(room):
    print("\n" + "=" * 20 + " room sensor values " + "=" * 20)
    sensor_list = await room.get_sensors_list()
    for sensor in sensor_list.sensors:
        if sensor.sensor_type == "room":
            room_sensor = sensor
            room_sensor_values = await room.get_sensor_values(room_sensor.uuid)
            print("type:", room_sensor_values.sensor_type)
            print("uuid:", room_sensor_values.uuid)
            print("nickname:", room_sensor_values.nickname)
            print("events:", room_sensor_values.events)


async def get_emo_settings(room):
    print("\n" + "=" * 20 + " room emo settings " + "=" * 20)
    emo_settings = await room.get_emo_settings()
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
    asyncio.run(main())
