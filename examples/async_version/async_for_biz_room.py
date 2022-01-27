"""Emo Platform API python example Executing method unique to room for buisness version.
"""

import asyncio

from emo_platform import BizAdvancedAsyncClient, BizBasicAsyncClient
from emo_platform.models import AccountInfo, BroadcastMsg

# Please replace "YOUR API KEY" with your api key to use biz version
api_key = "YOUR API KEY"

# business basic version
client = BizBasicAsyncClient()

# business advanced version
# client = BizAdvancedAsyncClient()


async def main():
    rooms_id = await client.get_rooms_id(api_key)

    # give api_key to room client
    room_client = client.create_room_client(api_key, rooms_id[0])

    # need not to give api_key to room client method
    # if you want to change api_key, please create another room_client for each api_key
    response = await room_client.get_msgs()
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
