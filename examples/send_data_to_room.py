"""Emo Platform API python example Sending data to room.
"""

import os
import time

from emo_platform import Client, Color, Head

THIS_FILE_PATH = os.path.abspath(os.path.dirname(__file__))

client = Client()
rooms_id_list = client.get_rooms_id()
# create room client
room = client.create_room_client(rooms_id_list[0])


def main():
    pass

    """
    Uncomment code block you want to execute.
    If you execute a lot, watch out for the API rate limit.
    """

    # audio_data_path = f"{THIS_FILE_PATH}/../assets/sample_audio.mp3"
    # send_audio_msg(audio_data_path)

    # image_data_path = f"{THIS_FILE_PATH}/../assets/sample_image.jpg"
    # send_image(image_data_path)

    # text = "こんにちは"
    # send_msg(text)

    # send_all_stamp_motions()

    # motion_data_path = f"{THIS_FILE_PATH}/../assets/sample_motion.json"
    # send_original_motion(motion_data_path) # send original motion by json file path

    # motion_data = {


# 	"head": [
# 	],
# 	"antenna": [
# 	],
# 	"led_cheek_l": [
# 	],
# 	"led_cheek_r": [
# 	],
# 	"led_play": [
# 	],
# 	"led_rec": [
# 	],
# 	"led_func": [
# 	]
# }
# send_original_motion(motion_data) # send original motion by dict data

# color = Color(100, 255, 155)
# print(change_led_color(color))

# head = Head(45, 10)
# move_to(head)

# send_all_preset_motions()


def send_audio_msg(audio_data_path):
    print("\n" + "=" * 20 + " room send audio msg " + "=" * 20)
    print(room.send_audio_msg(audio_data_path))


def send_image(image_data_path):
    print("\n" + "=" * 20 + " room send image " + "=" * 20)
    print(room.send_image(image_data_path))


def send_msg(text):
    print("\n" + "=" * 20 + " room send msg " + "=" * 20)
    print(room.send_msg(text))


def send_all_stamp_motions():
    print("\n" + "=" * 20 + " room send all stamps " + "=" * 20)
    stamp_list = client.get_stamps_list()
    for stamp in stamp_list.stamps:
        time.sleep(7)  # for avoiding rate limit
        print("\n" + "=" * 10 + " room send stamp " + "=" * 10)
        print(room.send_stamp(stamp.uuid))
        break


def send_original_motion(motion_data_path):
    print("\n" + "=" * 20 + " room send original motion " + "=" * 20)
    print(room.send_original_motion(motion_data_path))


def change_led_color(color):
    print("\n" + "=" * 20 + " room change led color " + "=" * 20)
    print(room.change_led_color(color))


def move_to(head):
    print("\n" + "=" * 20 + " room move to " + "=" * 20)
    print(room.move_to(head))


def send_all_preset_motions():
    print("\n" + "=" * 20 + " room send all motions " + "=" * 20)
    motion_list = client.get_motions_list()
    for motion in motion_list.motions:
        time.sleep(7)  # for avoiding rate limit
        print("\n" + "=" * 10 + " room send motion " + "=" * 10)
        print(room.send_motion(motion.uuid))
        break


if __name__ == "__main__":
    main()
