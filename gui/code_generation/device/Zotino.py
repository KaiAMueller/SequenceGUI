from .Device import Device


class Zotino(Device):
    def __init__(self, name):
        super().__init__(name)

    def generateInitCode(self):
        return f"""
        self.{self.name}.init()
        delay(1 * ms)"""
