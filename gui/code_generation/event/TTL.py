import gui.settings as settings

from .Event import Event


class TTLEvent(Event):

    def __init__(self, time, duration, device, state):
        """Turns a TTL device on or off"""
        Event.__init__(self, time=time, duration=duration, device=device)
        self.priority = 30
        self.state = state
        assert device.mode == "output", "TTL can only be either input or output, not both"

    def clone(self):
        return type(self)(time=self.time, duration=self.duration, device=self.device, state=self.state)

    def generatePrepareCode(self):
        return None

    def generateRunCode(self):
        return f"""
        self.{self.device.name}.{"on" if self.state else "off"}()"""


class TTLTriggerEvent(Event):

    MIN_REACTION_TIME = 1e-5

    def __init__(self, time, duration, device):
        """Waits for a TTL trigger"""
        Event.__init__(self, time=time, duration=duration, device=device)
        assert device.mode == "input", "TTL can only be either input or output, not both"

        self.durationVariableName = self.device.generateVariableName("trigger_duration")
        self.tEndVariableName = self.device.generateVariableName("tEnd")
        self.tEdgeVariableName = self.device.generateVariableName("tEdge")

    def clone(self):
        return type(self)(
            time=self.time,
            duration=self.duration,
            device=self.device,
        )

    def generatePrepareCode(self):
        return f"""
        self.{self.durationVariableName} = self.core.seconds_to_mu({self.duration} - {TTLTriggerEvent.MIN_REACTION_TIME})"""

    def generateRunCode(self):
        runCode = f"""
        {self.tEndVariableName} = self.{self.device.name}.gate_rising_mu(self.{self.durationVariableName})
        {self.tEdgeVariableName} = self.{self.device.name}.timestamp_mu({self.tEndVariableName})
        if {self.tEdgeVariableName} > 0:
            at_mu({self.tEdgeVariableName})"""
        if not settings.getRelativeTimestampsEnabled():
            runCode += f"""
            start_mu -= ({self.tEndVariableName} - {self.tEdgeVariableName})"""
        return runCode

    def getTimeCursorShift(self):
        return self.duration - TTLTriggerEvent.MIN_REACTION_TIME
