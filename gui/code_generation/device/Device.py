from ..event.Event import Event


class Device:
    def __init__(self, name, relatedDevices=None):
        self.name = name
        self.relatedDevices = relatedDevices or []  # give default value if argument is None
        self.events = []
        self.priority = 10  # high number -> high priority
        self.important = False
        self.eventIndex = 0
        self.variableTokens = {}
        self.functions = []

    def addEvent(self, event):
        if not isinstance(event, Event):
            raise Exception()
        if event in self.events:
            raise Exception()
        if event.device != self:
            raise Exception()
        self.events.append(event)
        for function in event.functions:
            if function not in self.functions:
                self.addFunction(function)

    def generateInitCode(self):
        return None

    def generateBuildCode(self):
        return None

    def addFunction(self, function):
        if function not in self.functions:
            self.functions.append(function)

    def generateVariableName(self, token):
        if token in self.variableTokens:
            self.variableTokens[token] += 1
        else:
            self.variableTokens[token] = 0
        return f"{self.name}_{token}_{self.variableTokens[token]}"
