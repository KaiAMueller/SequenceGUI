from .Device import Device


class CoreDevice(Device):

    def __init__(self):
        super().__init__("core", [])
        self.priority = 100
        self.important = True

    def generateInitCode(self):
        return """
        self.core.reset()
        delay(10*ms)
        self.core.break_realtime()
        delay(10*ms)"""
