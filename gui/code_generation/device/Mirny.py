from .Device import Device


class Mirny(Device):
    def __init__(self, name, channel, cpld):
        super().__init__(name, [cpld])
        self.enabled = None
        self.cpld = cpld
        self.channel = channel
        self.almaznyDeviceName = None
        self.cpld.addChannel(self)

    def setAlmaznyDeviceName(self, almaznyDeviceName):
        self.almaznyDeviceName = almaznyDeviceName

    def generate_setattr_string_code(self):
        code = f"""
        self.setattr_device("{self.name}")"""
        if self.almaznyDeviceName is not None:
            code += f"""
        self.setattr_device("{self.almaznyDeviceName}")"""
        return code

    def generateInitCode(self):
        return ""
        code = f"""
        self.core.break_realtime()
        self.{self.name}.sync() # usually init but there seems to be a bug with mirny init, sync is a workaround
        self.core.break_realtime()"""
        return code

    def addRamEvent(self, ramEvent):
        self.ramEvents.append(ramEvent)


class MirnyCPLD(Device):
    def __init__(self, name):
        super().__init__(name)
        self.priority = 20
        self.channels = []
        self.skipInit = False

    def addChannel(self, channel):
        if channel not in self.channels:
            self.channels.append(channel)

    def generateInitCode(self):
        if self.skipInit:
            return ""
        else:
            return f"""
        self.{self.name}.init()"""
