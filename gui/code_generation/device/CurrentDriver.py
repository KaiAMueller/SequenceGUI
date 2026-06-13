from .Device import Device


class CurrentDriver(Device):
    def __init__(self, name):
        super().__init__(name)
        self.handlerVariableName = f"{name}_handler"

    def generateInitCode(self):
        return ""

    def generateBuildCode(self):
        return f"""
        self.{self.handlerVariableName} = CurrentDriverHandler(self.{self.name})
"""
