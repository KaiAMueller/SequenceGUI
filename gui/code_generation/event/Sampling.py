from gui.widgets.Log import log

from .Event import Event


class SampleEvent(Event):

    def __init__(self, time, device, sampleRate, duration):
        """Generates all events needed for sampling for the given duration"""
        Event.__init__(self, time=time, duration=duration, device=device)
        self.sampleRate = sampleRate
        self.duration = duration
        if self.duration is not None and sampleRate is not None:
            self.numberOfSamples = int(sampleRate * self.duration)
            if self.numberOfSamples == 0:
                log("Error: Number of samples is 0")
            self.samplePeriod = 1 / sampleRate
        self.priority = 0.2

    def dataString(self):
        return "d" + self.device.name + "_" + str(self.timeIndex)

    def clone(self):
        return type(self)(
            time=self.time,
            device=self.device,
            duration=self.duration,
            sampleRate=self.sampleRate,
        )

    def setValue(self, sampleRate):
        self.numberOfSamples = int(sampleRate * self.duration)
        self.samplePeriod = 1 / sampleRate if sampleRate != 0 else float("inf")

    def generatePrepareCode(self):
        # create variable thats stores the data sampled during this events duration
        if self.numberOfSamples > 0:
            return f"""
        self.{self.dataString()} = np.full(({self.numberOfSamples},8),0,dtype=float)"""
        return None

    def generateRunCode(self):
        return f"""
        for i in range({self.numberOfSamples}):
            with parallel:
                self.{self.device.name}.sample(self.{self.dataString()}[i])
                delay({self.samplePeriod})"""

    def generateAnalyzeCode(self):
        # store sampled data into a dataset for every channel
        if self.numberOfSamples > 0:
            return f"""
        for i in range(8):
            self.set_dataset("{self.dataString()+"_data"}_ch_" + str(i), self.{self.dataString()}[:,i])
        self.set_dataset("{self.dataString()+"_samplerate"}", {self.sampleRate:.3f})"""
        return None

    def generateImportCode(self):
        return "import numpy as np"
