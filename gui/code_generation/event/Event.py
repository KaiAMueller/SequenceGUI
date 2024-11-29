class Event:
    def __init__(self, time, duration, device):
        self.time = time
        self.duration = duration
        self.device = device
        self.priority = 10  # high number -> high priority
        self.timeIndex = None
        self.functions = []
        if device is not None:
            device.addEvent(self)

    def clone(self):
        raise NotImplementedError(type(self))

    def generateImportCode(self):
        return None

    def generatePrepareCode(self):
        return None

    def generateRunCode(self):
        return None

    def generateAnalyzeCode(self):
        return None

    def getTimeCursorShift(self):
        return 0
