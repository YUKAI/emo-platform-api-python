class Color:
    """
    BOCCO emoのほっぺの色。

    Parameters
    ----------
    red : int
        赤の輝度(0~255)。
    green : int
        緑の輝度(0~255)。
    blue : int
        青の輝度(0~255)。
    """

    def __init__(self, red: int, green: int, blue: int):
        self.red =  self._check_constraints(red)
        self.green = self._check_constraints(green)
        self.blue = self._check_constraints(blue)

    def _check_constraints(self, value: int, min_val: int = 0, max_val: int = 255):
        return max(min(value, max_val), min_val)

class Head:
    """
    BOCCO emoの首の角度。

    Parameters
    ----------
    angle: int
        左右方向の首の角度(-45~45)。
    vertical_angle: int
        上下方向の首の角度(-20~20)。

    """
    def __init__(self, angle: int = 0, vertical_angle: int = 0):
        self.angle = self._check_constraints(angle, -45, 45)
        self.vertical_angle = self._check_constraints(vertical_angle, -20, 20)

    def _check_constraints(self, value: int, min_val: int, max_val: int):
        return max(min(value, max_val), min_val)

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
    def __init__(self, url: str, description: str = ""):
        self.url = url
        self.description = description
