from dataclasses import dataclass


@dataclass
class Tokens:
    """API利用に必要なトークンの情報。

    Note
    ----------
    トークンは `ダッシュボード <https://staging-platform-api.bocco.me/dashboard/login>`_ にログイン後に確認できます。

    """

    access_token: str = ""
    """
    アクセストークン
    """

    refresh_token: str = ""
    """
    リフレッシュトークン
    """


@dataclass
class Color:
    """BOCCO emoのほっぺの色。

    Note
    ----------
    範囲外の値を入れた際は、最小値と最大値のうち近い方の値になります。

    """

    red: int = 0
    """
    赤の輝度(0~255)
    """

    green: int = 0
    """
    緑の輝度(0~255)
    """

    blue: int = 0
    """
    青の輝度(0~255)
    """

    def __post_init__(self):
        self.red = self._check_constraints(self.red)
        self.green = self._check_constraints(self.green)
        self.blue = self._check_constraints(self.blue)

    def _check_constraints(self, value: int, min_val: int = 0, max_val: int = 255):
        return max(min(value, max_val), min_val)


@dataclass
class Head:
    """
    BOCCO emoの首の角度。

    Note
    ----------
    範囲外の値を入れた際は、最小値と最大値のうち近い方の値になります。

    """

    angle: float = 0
    """
    左右方向の首の角度(-45~45)
    """

    vertical_angle: float = 0
    """
    上下方向の首の角度(-20~20)
    """

    def __post_init__(self):
        self.angle = self._check_constraints(self.angle, -45, 45)
        self.vertical_angle = self._check_constraints(self.vertical_angle, -20, 20)

    def _check_constraints(self, value: float, min_val: float, max_val: float):
        return max(min(value, max_val), min_val)


@dataclass
class WebHook:
    """BOCCO emoに設定するWebhook。"""

    url: str
    """
    Webhookの通知先のurl
    """

    description: str = ""
    """
    Webhookの設定に関する説明書き
    """


@dataclass
class AccountInfo:
    """
    BOCCOアカウント情報。
    """

    name: str
    """
    アカウント名(1~20文字)
    """

    name_furigana: str
    """
    アカウント名のふりがな(平仮名表記)(1~20文字)
    """

    organization_name: str
    """
    組織名(1~100文字)
    """

    organization_unit_name: str
    """
    部署名(1~100文字)
    """

    phone_number: str
    """
    電話番号(10~11文字のハイフンなし)
    """


@dataclass
class BroadcastMsg:
    """
    配信メッセージの情報。
    """

    title: str
    """
    配信メッセージのタイトル
    """

    text: str
    """
    配信するメッセージ
    """

    executed_at: int = 0
    """
    配信予定時刻(UNIX Timestamp形式)
    """

    immediate: bool = False
    """
    即時配信にするかどうか

    Note
    ----------
    immediateをTrueにした場合、executed_atに書いた時刻は反映されず、即時配信となります。

    """
