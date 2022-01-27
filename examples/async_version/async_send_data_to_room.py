"""Emo Platform API python example Sending data to room.
"""

import asyncio
import os

from emo_platform import (
    AsyncClient,
    Color,
    Head,
)

THIS_FILE_PATH = os.path.abspath(os.path.dirname(__file__))

# personal version
client = AsyncClient()

room = []


async def main():
    global room
    rooms_id_list = await client.get_rooms_id()
    # create room client
    room = client.create_room_client(rooms_id_list[0])

    """
    Uncomment code block you want to execute.
    If you execute a lot, watch out for the API rate limit.
    """

    # audio_data_path = f"{THIS_FILE_PATH}/../../assets/sample_audio.mp3"
    # await send_audio_msg(audio_data_path)

    # image_data_path = f"{THIS_FILE_PATH}/../../assets/sample_image.jpg"
    # await send_image(image_data_path)

    # text = "こんにちは"
    # await send_msg(text)

    # await send_all_stamp_motions()

    # motion_data_path = f"{THIS_FILE_PATH}/../../assets/sample_motion.json"
    # await send_original_motion(motion_data_path)

    # motion_data = {
    #     "head": [
    #     ],
    #     "antenna": [
    #     ],
    #     "led_cheek_l": [
    #     ],
    #     "led_cheek_r": [
    #     ],
    #     "led_play": [
    #     ],
    #     "led_rec": [
    #     ],
    #     "led_func": [
    #     ]
    # }
    # await send_original_motion(motion_data) # send original motion by dict data

    # color = Color(100, 255, 155)
    # await change_led_color(color)

    # head = Head(45, 10)
    # await move_to(head)

    # await send_all_preset_motions()


async def send_audio_msg(audio_data_path):
    print("\n" + "=" * 20 + " room send audio msg " + "=" * 20)
    print(await room.send_audio_msg(audio_data_path))


async def send_image(image_data_path):
    print("\n" + "=" * 20 + " room send image " + "=" * 20)
    print(await room.send_image(image_data_path))


async def send_msg(text):
    print("\n" + "=" * 20 + " room send msg " + "=" * 20)
    print(await room.send_msg(text))


async def send_all_stamp_motions():
    print("\n" + "=" * 20 + " room send all stamps " + "=" * 20)
    stamp_list = await client.get_stamps_list()
    for stamp in stamp_list.stamps:
        await asyncio.sleep(7)  # for avoiding rate limit
        print("\n" + "=" * 10 + " room send stamp " + "=" * 10)
        print(await room.send_stamp(stamp.uuid))


async def send_original_motion(motion_data_path):
    print("\n" + "=" * 20 + " room send original motion " + "=" * 20)
    print(await room.send_original_motion(motion_data_path))


async def change_led_color(color):
    print("\n" + "=" * 20 + " room change led color " + "=" * 20)
    print(await room.change_led_color(color))


async def move_to(head):
    print("\n" + "=" * 20 + " room move to " + "=" * 20)
    print(await room.move_to(head))


async def send_all_preset_motions():
    print("\n" + "=" * 20 + " room send all motions " + "=" * 20)
    motion_list = await client.get_motions_list()
    for motion in motion_list.motions:
        await asyncio.sleep(7)  # for avoiding rate limit
        print("\n" + "=" * 10 + " room send motion " + "=" * 10)
        print(await room.send_motion(motion.uuid))


if __name__ == "__main__":
    asyncio.run(main())
