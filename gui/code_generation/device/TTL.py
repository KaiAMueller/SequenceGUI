from .Device import Device


class TTL(Device):
    def __init__(self, name, mode="output"):
        super().__init__(name)
        self.mode = mode

    def generateInitCode(self):
        code = f"""
        self.{self.name}.{self.mode}()"""
        return code
