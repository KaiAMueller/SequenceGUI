from .Device import Device


class RPC(Device):
    def __init__(self, name):
        super().__init__(name)
        self.important = True
