import pprint
from typing import List, Union

from pydantic import BaseModel


class PrintModel(BaseModel):
    def __str__(self):
        return pprint.pformat(self.dict())


class EmoAccountInfo(PrintModel):
    """BOCCOアカウント情報(Personal版)。"""

    name: str
    """アカウント名
    """

    email: str
    """アカウントのメールアドレス
    """

    profile_image: str
    """アカウントのプロフィール画像のURL
    """

    uuid: str
    """アカウントのid
    """

    plan: str
    """アカウントのプラン
    """


class EmoBizAccountInfo(PrintModel):
    """BOCCOアカウント情報(Business版)。"""

    account_id: int
    """アカウントのid
    """

    name: str
    """アカウント名
    """

    name_furigana: str
    """アカウント名のふりがな
    """

    email: str
    """アカウント名のメールアドレス
    """

    organization_name: str
    """組織名
    """

    organization_unit_name: str
    """部署名
    """

    phone_number: str
    """電話番号
    """

    plan: str
    """アカウントのプラン
    """


class EmoTokens(PrintModel):
    """API利用に必要なトークンの情報。"""

    access_token: str
    """アクセストークン
    """

    refresh_token: str
    """リフレッシュトークン
    """


class Listing(PrintModel):
    offset: Union[int, float]
    limit: Union[int, float]
    total: Union[int, float]


class EmoRoomMember(PrintModel):
    """部屋に参加しているメンバーの情報"""

    uuid: str
    """メンバーのid
    """

    user_type: str
    """メンバーの種別
    """

    nickname: str
    """メンバーのニックネーム
    """

    profile_image: str
    """メンバーのプロフィール画像のURL
    """


class RoomInfo(PrintModel):
    """部屋の情報"""

    uuid: str
    """部屋のid
    """

    name: str
    """部屋の名前
    """

    room_type: str
    """部屋の種類
    """

    room_members: List[EmoRoomMember]
    """部屋に参加しているメンバーの一覧
    """


class EmoRoomInfo(PrintModel):
    """ユーザーが参加している部屋の一覧情報"""

    listing: Listing

    rooms: List[RoomInfo]
    """ユーザーが参加している部屋の一覧
    """


class EmoMessage(PrintModel):
    """部屋に投稿されたテキストメッセージの内容"""

    ja: str


class EmoMessageInfo(PrintModel):
    """部屋に投稿されたメッセージの情報"""

    sequence: int
    """メッセージの順序関係を示すシーケンス値

    数字の意味は、`こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/messages>`_ をご覧ください。
    """

    unique_id: str
    """メッセージのid
    """

    user: EmoRoomMember
    """メッセージを投稿したメンバーの情報
    """

    message: EmoMessage
    """テキストメッセージの内容
    """

    media: str
    """メッセージのタイプ

    Note
    ----
    text
        テキストメッセージ
    audio
        音声メッセージ
    image
        画像メッセージ
    stamp
        スタンプメッセージ

    """

    audio_url: str
    """送信された音声ファイルのURL
    """

    image_url: str
    """送信された画像ファイルのURL
    """

    lang: str
    """メッセージの言語
    """


class EmoMsgsInfo(PrintModel):
    """部屋に投稿されたメッセージの一覧情報"""

    messages: List[EmoMessageInfo]
    """部屋に投稿されたメッセージの一覧
    """


class EmoStamp(PrintModel):
    """スタンプの情報"""

    uuid: str
    """スタンプのid
    """

    name: str
    """スタンプの名前
    """

    summary: str
    """スタンプの内容説明
    """

    image: str
    """スタンプ画像のURL
    """


class EmoStampsInfo(PrintModel):
    """利用可能なスタンプの一覧情報"""

    listing: Listing

    stamps: List[EmoStamp]
    """スタンプの一覧
    """


class EmoMotion(PrintModel):
    """モーションの情報"""

    uuid: str
    """モーションのid
    """

    name: str
    """モーションの名前
    """

    preview: str
    """モーションの音声ファイルのURL
    """


class EmoMotionsInfo(PrintModel):
    """利用可能なモーションの一覧情報"""

    listing: Listing
    motions: List[EmoMotion]
    """モーションの一覧
    """


class EmoWebhookInfo(PrintModel):
    """現在設定されているWebhookの情報"""

    description: str
    """Webhookの設定に関する説明書き
    """

    events: List[str]
    """Webhookを受け取る対象のイベントの一覧
    """

    status: str
    """Webhookの設定状態
    """

    secret: str
    """WebhookリクエストのHTTP Headerに含まれるX-Platform-API-Secretと同一の文字列。

    この文字列とX-Platform-API-Secretの値が同一か確かめることで、第三者からの予期せぬリクエストを防ぐことができます。
    """

    url: str
    """Webhookの送信先のURL
    """


class EmoSensor(PrintModel):
    """BOCCO emoとペアリングされているセンサ情報"""

    uuid: str
    """センサのid
    """

    sensor_type: str
    """センサの種類
    """

    nickname: str
    """センサのニックネーム
    """

    signal_strength: int
    """センサの信号の強さ
    """

    battery: int
    """センサの残りバッテリー
    """


class EmoSensorsInfo(PrintModel):
    """BOCCO emoとペアリングされているセンサ情報の一覧"""

    sensors: List[EmoSensor]
    """ベアリングされているセンサの一覧
    """


class EmoRoomSensorEvent(PrintModel):
    """部屋センサの送信値"""

    temperature: Union[int, float]
    """温度
    """

    humidity: Union[int, float]
    """湿度
    """

    illuminance: Union[int, float]
    """照度
    """


class EmoRoomSensorInfo(PrintModel):
    """部屋センサの送信値の一覧"""

    sensor_type: str
    """センサの種類
    """

    uuid: str
    """センサのid
    """

    nickname: str
    """センサのニックネーム
    """

    events: List[EmoRoomSensorEvent]
    """センサの送信値の一覧
    """


class EmoSettingsInfo(PrintModel):
    """現在のBOCCO emoの設定値"""

    nickname: str
    """ニックネーム
    """

    wakeword: str
    """ウェイクアップワード
    """

    volume: int
    """音量
    """

    voice_pitch: int
    """声の高さ
    """

    voice_speed: int
    """話すスピード
    """

    lang: str
    """言語設定
    """

    serial_number: str
    """シリアルナンバー
    """

    timezone: str
    """タイムゾーン
    """

    zip_code: str
    """郵便番号
    """


class EmoBroadcastMessage(PrintModel):
    """配信メッセージの情報"""

    id: int
    """配信メッセージのid
    """

    channel_uuid: str
    """チャンネルのid
    """

    title: str
    """配信メッセージのタイトル
    """

    text: str
    """配信メッセージの内容
    """

    executed_at: int
    """配信時間
    """

    finished: bool
    """配信済みか
    """

    success: bool
    """配信に成功したか
    """

    failed: bool
    """配信に失敗したか
    """


class EmoBroadcastInfoList(PrintModel):
    """配信メッセージの一覧情報"""

    listing: Listing

    messages: List[EmoBroadcastMessage]
    """配信メッセージの一覧
    """


class EmoBroadcastMessageDetail(PrintModel):
    """配信メッセージの詳細"""

    room_uuid: str
    """配信された部屋のid
    """

    room_name: str
    """配信された部屋の名前
    """

    success: bool
    """配信メッセージの詳細
    """

    status_code: int
    """配信リクエストのステータスコード
    """

    description: str
    """配信リクエストの結果
    """

    executed_at: int
    """配信時間
    """


class EmoBroadcastInfo(PrintModel):
    """配信メッセージの詳細情報"""

    message: EmoBroadcastMessage
    """配信メッセージの情報
    """

    details: List[EmoBroadcastMessageDetail]
    """配信メッセージの詳細
    """


class EmoKind(PrintModel):
    """様々な種別に関する情報"""

    kind: str


class EmoWebhookTriggerWord(PrintModel):
    """Webhookで受信したトリガーワードイベントに関する情報"""

    trigger_word: EmoKind
    """トリガーワードの種別の情報

        default_bocco
            「ねえボッコ」の呼びかけに反応した場合
        default_emo
            「エモちゃん」の呼びかけに反応した場合
        user_nickname
            ニックネームでの呼びかけに反応した場合
    """


class EmoPerformedBy(PrintModel):
    """録音が実行されたきっかけに関する情報"""

    performed_by: str
    """録音が実行されたきっかけのアクションを示す値

        record_button
            本体の録音ボタンが押された場合の値
        vui_command
            音声コマンドでの録音命令が実施された場合の値
    """


class EmoWebhookRecording(PrintModel):
    """Webhookで受信した録音イベントに関する情報"""

    recording: EmoPerformedBy
    """録音が実行されたきっかけに関する情報
    """


class EmoMinutes(PrintModel):
    """Webhookで受信した音声イベントコマンドのタイマーでセットした時間(分)に関する情報"""

    minutes: str


class EmoTime(PrintModel):
    """Webhookで受信した音声イベントコマンドのアラームのセット時刻に関する情報"""

    time: str


class EmoArea(PrintModel):
    """Webhookで受信した音声イベントコマンドの天気の場所に関する情報"""

    area: str


class EmoVolume(PrintModel):
    """Webhookで受信した音声イベントコマンドの音量の値に関する情報"""

    volume: str


class EmoVuiCommand(PrintModel):
    """音声コマンドに関する情報"""

    kind: str
    """音声コマンドの種別を示す値
    """

    parameters: Union[EmoMinutes, EmoTime, EmoArea, EmoVolume]
    """「エモちゃん、10時にアラーム設定して」のように、パラメータ付きで実行されたVUIの詳細を示す値

    「エモちゃん、しゃべって」のように、パラメータを持たない音声コマンドが実行された場合はparametersの値は付与されません。
    """


class EmoWebhookVuiCommand(PrintModel):
    """Webhookで受信した音声コマンドイベントに関する情報"""

    vui_command: Union[EmoVuiCommand, EmoKind]
    """音声コマンドとトリガワードの種類に関する情報
    """


class EmoWebhookMotion(PrintModel):
    """Webhookで受信したモーション実行完了イベントに関する情報"""

    motion: EmoKind
    """実行されたモーションの種別を示す値
    """


class EmoTalk(PrintModel):
    """BOCCO emoが発話した内容に関する情報"""

    talk: str
    """発話した内容を示すテキスト
    """


class EmoWebhookEmoTalk(PrintModel):
    """Webhookで受信した発話完了イベントに関する情報"""

    emo_talk: EmoTalk
    """BOCCO emoが発話した内容に関する情報
    """


class EmoWebhookAccel(PrintModel):
    """Webhookで受信した内蔵加速度センサイベントに関する情報"""

    accel: EmoKind
    """レーダセンサが検知したイベントを示す値

        normal
            直立静止している状態に移行した場合の値
        upside_down
            逆さまの状態に移行した場合の値
        lying_down
            横倒しの状態に移行した場合の値
        shaken
            揺さぶられた状態に移行した場合の値
        beaten
            つつかれた状態に移行した場合の値
        dropped
            落とされた状態に移行した場合の値
        lift
            持ち上げられた状態に移行した場合の値
    """


class EmoWebhookIlluminance(PrintModel):
    """Webhookで受信した内蔵照度センサイベントに関する情報"""

    illuminance: EmoKind
    """照度センサが検知したイベントを示す値

        brighter
            明るくなった時の値
        darker
            暗くなった時の値
    """


class EmoRadar(PrintModel):
    """レーダセンサが検知したイベントの情報"""

    begin: bool
    """BOCCO emoの近くに人がいる時に、true が設定されます。
    """

    end: bool
    """BOCCO emoの近くから人が立ち去った時に、true が設定されます。
    """

    near_begin: bool
    """BOCCO emoのすぐ近くに人がいる時に、true が設定されます。
    """

    near_end: bool
    """BOCCO emoのすぐ近くから人が立ち去った時に、true が設定されます。
    """


class EmoWebhookRadar(PrintModel):
    """Webhookで受信した内蔵レーダーセンサイベントに関する情報"""

    radar: EmoRadar
    """レーダセンサが検知したイベントの情報
    """


class EmoWebhookMessage(PrintModel):
    """Webhookで受信した新規メッセージ受信イベントに関する情報"""

    message: EmoMessageInfo
    """BOCCO emoが受信したメッセージを示す値
    """


class EmoWebhookSensorMessage(PrintModel):
    """センサの通知内容"""

    sequence: int
    """通知された時間を示す値

    数字の意味は、`こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#get-/v1/rooms/-room_uuid-/messages>`_ をご覧ください。
    """

    unique_id: str
    """センサ通知のid
    """

    user: EmoRoomMember
    """センサのメンバー情報
    """

    message_type: str
    """メッセージの種類

    sensor固定です。
    """

    sensor_action: str
    """センサ通知の種別
    """

    lang: str
    """言語設定
    """


class EmoWebhookMovementSensor(PrintModel):
    """Webhookで受信した振動センサ反応イベントに関する情報"""

    movement_sensor: EmoWebhookSensorMessage
    """振動センサの通知内容
    """


class EmoWebhookLockSensor(PrintModel):
    """Webhookで受信した鍵センサ反応イベントに関する情報"""

    lock_sensor: EmoWebhookSensorMessage
    """鍵センサの通知内容
    """


class EmoWebhookHumanSensor(PrintModel):
    """Webhookで受信した人感センサ反応イベントに関する情報"""

    human_sensor: EmoWebhookSensorMessage
    """人感センサの通知内容
    """


class EmoWebhookRoomSensor(PrintModel):
    """Webhookで受信した部屋センサ反応イベントに関する情報"""

    room_sensor: EmoWebhookSensorMessage
    """部屋センサの通知内容
    """


class EmoWebhookBody(PrintModel):
    """受信したWebhookの内容"""

    request_id: str
    """リクエストの同一性を示す、一意の文字列
    """

    uuid: str
    """BOCCO emoを識別する一意なID
    """

    serial_number: str
    """BOCCO emoの製造番号
    """

    nickname: str
    """BOCCO emoに設定されているニックネーム
    """

    timestamp: int
    """イベントが発生した時刻を示すUNIX Timestamp
    """

    event: str
    """発生したイベントの種別を示す文字列

    Note
    ----
    eventの種類は、`こちらのページ <https://platform-api.bocco.me/dashboard/api-docs#put-/v1/webhook/events>`_ から確認できます。
    """

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
        dict,
    ]
    """発生したイベントの詳細を示すオブジェクト

    イベントの種類に応じてデータ構造が変わります。


    Attention
    ----
    eventの種類がfunction_button.pressedの時、dataは空の辞書 {} となります。

    """

    receiver: str
    """Webhook受信者を示すid

        Personal版の場合
            :func:`get_account_info` から確認できるBOCCOアカウントのuuid
        Business版の場合
            法人アカウントでログインした時の `ダッシュボード <https://platform-api.bocco.me/dashboard/>`_
            から確認できる法人向けAPIキーと同じ文字列
    """


class EmoPostConversation(PrintModel):
    """対話セッションのレスポンス"""

    session_id: str
    """対話セッションID
    """


def parse_webhook_body(body: dict) -> EmoWebhookBody:
    """受信したwebhookリクエストのボディのJSONペイロードのパース

    Parameters
    ----------
    body : dict
        受信したwebhookリクエストのボディのJSONペイロード

    Returns
    -------
    emo_webhook_body : EmoWebhookBody
        パースされたボディ

    """

    return EmoWebhookBody(**body)
