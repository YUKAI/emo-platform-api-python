from dataclasses import dataclass


@dataclass
class Tokens:
    access_token: str = ""
    refresh_token: str = ""


@dataclass
class Color:
    """BOCCO emoのほっぺの色。

    Parameters
    ----------
    red : int, default 0
        赤の輝度(0~255)。
    green : int, default 0
        緑の輝度(0~255)。
    blue : int, default 0
        青の輝度(0~255)。

    Note
    ----------
    範囲外の値を入れた際は、最小値と最大値のうち近い方の値になります。

    """

    red: int = 0
    green: int = 0
    blue: int = 0

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

    Parameters
    ----------
    angle: float, default 0
        左右方向の首の角度(-45~45)。
    vertical_angle: float, default 0
        上下方向の首の角度(-20~20)。

    Note
    ----------
    範囲外の値を入れた際は、最小値と最大値のうち近い方の値になります。

    """

    angle: float = 0
    vertical_angle: float = 0

    def __post_init__(self):
        self.angle = self._check_constraints(self.angle, -45, 45)
        self.vertical_angle = self._check_constraints(self.vertical_angle, -20, 20)

    def _check_constraints(self, value: float, min_val: float, max_val: float):
        return max(min(value, max_val), min_val)


@dataclass
class WebHook:
    """
    BOCCO emoに設定するWebhook。

    Parameters
    ----------
    url: str
        Webhookの通知先のurl。
    description: str, default ""
        Webhookの設定に関する説明書き。

    """

    url: str
    description: str = ""


@dataclass
class AccountInfo:
    name: str
    name_furigana: str
    organization_name: str
    organization_unit_name: str
    phone_number: str


@dataclass
class BroadcastMsg:
    title: str
    text: str
    executed_at: int = 0
    immediate: bool = False
