from typing import List, Union

from pydantic import BaseModel


class EmoAccountInfo(BaseModel):
    name: str
    email: str
    profile_image: str
    uuid: str
    plan: str


class EmoTokens(BaseModel):
    access_token: str
    refresh_token: str


class Listing(BaseModel):
    offset: Union[int, float]
    limit: Union[int, float]
    total: Union[int, float]


class EmoRoomMember(BaseModel):
    uuid: str
    user_type: str
    nickname: str
    profile_image: str


class RoomInfo(BaseModel):
    uuid: str
    name: str
    room_type: str
    room_members: List[EmoRoomMember]


class EmoRoomInfo(BaseModel):
    listing: Listing
    rooms: List[RoomInfo]


class EmoMessage(BaseModel):
    ja: str


class EmoMessageInfo(BaseModel):
    sequence: int
    unique_id: str
    user: EmoRoomMember
    message: EmoMessage
    media: str
    audio_url: str
    image_url: str
    lang: str


class EmoMsgsInfo(BaseModel):
    messages: List[EmoMessageInfo]


class EmoStamp(BaseModel):
    uuid: str
    name: str
    summary: str
    image: str


class EmoStampsInfo(BaseModel):
    listing: Listing
    stamps: List[EmoStamp]


class EmoMotion(BaseModel):
    uuid: str
    name: str
    preview: str


class EmoMotionsInfo(BaseModel):
    listing: Listing
    motions: List[EmoMotion]


class EmoWebhookInfo(BaseModel):
    description: str
    events: List[str]
    status: str
    secret: str
    url: str


class EmoSensor(BaseModel):
    uuid: str
    sensor_type: str
    nickname: str
    signal_strength: int
    battery: int


class EmoSensorsInfo(BaseModel):
    sensors: List[EmoSensor]


class EmoRoomSensorEvent(BaseModel):
    temperature: Union[int, float]
    humidity: Union[int, float]
    illuminance: Union[int, float]


class EmoRoomSensorInfo(BaseModel):
    sensor_type: str
    uuid: str
    nickname: str
    events: List[EmoRoomSensorEvent]


class EmoSettingsInfo(BaseModel):
    nickname: str
    wakeword: str
    volume: int
    voice_pitch: int
    voice_speed: int
    lang: str
    serial_number: str
    timezone: str
    zip_code: str
