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

class EmoKind(BaseModel):
    kind: str

class EmoWebhookTriggerWord(BaseModel):
    trigger_word: EmoKind

class EmoPerformedBy(BaseModel):
    performed_by: str

class EmoWebhookRecording(BaseModel):
    recording: EmoPerformedBy

class EmoMinutes(BaseModel):
    minutes: str

class EmoTime(BaseModel):
    time: str

class EmoArea(BaseModel):
    area: str

class EmoVolume(BaseModel):
    volume: str

class EmoVuiCommand(BaseModel):
    kind: str
    parameters: Union[EmoMinutes, EmoTime, EmoArea, EmoVolume]

class EmoWebhookVuiCommand(BaseModel):
    vui_command : Union[EmoVuiCommand, EmoKind]

class EmoWebhookMotion(BaseModel):
    motion: EmoKind

class EmoTalk(BaseModel):
    talk: str

class EmoWebhookEmoTalk(BaseModel):
    emo_talk: EmoTalk

class EmoWebhookAccel(BaseModel):
    accel: EmoKind

class EmoWebhookIlluminance(BaseModel):
    illuminance: EmoKind

class EmoRadar(BaseModel):
    begin:      bool
    end:        bool
    near_begin: bool
    near_end:   bool

class EmoWebhookRadar(BaseModel):
    radar: EmoRadar

class EmoWebhookMessageBody(BaseModel):
    sequence: int
    unique_id: str
    user: EmoRoomMember
    message: EmoMessage
    media: str
    lang: str

class EmoWebhookMessage(BaseModel):
    message: EmoWebhookMessageBody

class EmoWebhookMovementSensor(BaseModel):
    message: EmoWebhookMessageBody

class EmoWebhookLockSensor(BaseModel):
    message: EmoWebhookMessageBody

class EmoWebhookHumanSensor(BaseModel):
    message: EmoWebhookMessageBody

class EmoWebhookRoomSensor(BaseModel):
    message: EmoWebhookMessageBody

class EmoWebhookBody(BaseModel):
    request_id: str
    uuid: str
    serial_number: str
    nickname: str
    timestamp: int
    event: str
    data: Union[
        EmoWebhookTriggerWord,
        EmoWebhookRecording,
        EmoWebhookVuiCommand,
        EmoWebhookMotion,
        EmoWebhookEmoTalk,
        EmoWebhookAccel,
        EmoWebhookIlluminance,
        EmoWebhookRadar,
        EmoWebhookMessage,
        EmoWebhookMovementSensor,
        EmoWebhookLockSensor,
        EmoWebhookHumanSensor,
        EmoWebhookRoomSensor,
        dict
    ]
    receiver: str
