import asyncio

from emo_platform import AsyncClient


async def main():
    client = await AsyncClient()
    rooms_id_list = await client.get_rooms_id()
    room = client.create_room_client(rooms_id_list[0])
    await get_msgs(room)
    await get_sensors_list(room)
    await get_sensor_values(room)
    await get_emo_settings(room)


async def get_msgs(room):
    print("\n" + "=" * 20 + " room msgs " + "=" * 20)
    print(await room.get_msgs())


async def get_sensors_list(room):
    print("\n" + "=" * 20 + " room sensors list " + "=" * 20)
    print(await room.get_sensors_list())


async def get_sensor_values(room):
    print("\n" + "=" * 20 + " room sensor values " + "=" * 20)
    sensor_list = await room.get_sensors_list()
    print(await room.get_sensor_values(sensor_list["sensors"][0]["uuid"]))


async def get_emo_settings(room):
    print("\n" + "=" * 20 + " room emo settings " + "=" * 20)
    print(await room.get_emo_settings())


if __name__ == "__main__":
    asyncio.run(main())
