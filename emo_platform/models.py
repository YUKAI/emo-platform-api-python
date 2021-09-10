
class Color:
	def __init__(self, red: int, green: int, blue: int):
		self.red = red
		self.green = green
		self.blue = blue

class Head:
	def __init__(self, angle: int = 0, vertical_angle: int = 0):
		self.angle = angle
		self.vertical_angle = vertical_angle

class WebHook:
	def __init__(self, url :str, description : str = ""):
		self.url = url
		self.description = description
