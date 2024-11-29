from .Event import Event


class WaitEvent(Event):

    def __init__(self, time, duration, device):
        """Issues wait_until(now_mu()), eg to make sure that the kernel does not quit early"""
        Event.__init__(self, time=time, duration=duration, device=device)

    def clone(self):
        return type(self)(time=self.time, duration=self.duration, device=self.device)

    def generateRunCode(self):
        return f"""
        self.{self.device.name}.wait_until_mu(now_mu())"""

    def generatePrepareCode(self):
        return None

    def generateAnalyzeCode(self):
        return None
