from gui.widgets.Log import log

from .Event import Event

GAIN_TO_MU = {
    "1x": 0,
    "10x": 1,
    "100x": 2,
    "1000x": 3,
}

class SampleEvent(Event):

    def __init__(self, time, device, sampleRate, duration, gains):
        Event.__init__(self, time=time, duration=duration, device=device)

        self.sampleRate = sampleRate
        self.duration = duration
        self.gains = gains

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
            gains=self.gains.copy(),
        )

    def setValue(self, sampleRate):
        self.numberOfSamples = int(sampleRate * self.duration)
        self.samplePeriod = 1 / sampleRate if sampleRate != 0 else float("inf")

    
    
    
    def generatePrepareCode(self):
        if self.numberOfSamples > 0:
            code = (
                f"self.{self.dataString()} = "
                f"np.full(({self.numberOfSamples}, 8), 0, dtype=np.int32)"
            )
            return "\n" + " " * 8 + code
        return None




    
    def generateRunCode(self):
        lines = []

        # Configure gain for all 8 Sampler channels
        for channel, gain in enumerate(self.gains):
            lines.append(
                f"self.{self.device.name}.set_gain_mu("
                f"{channel}, {GAIN_TO_MU[gain]})"
            )
        
        # Generate sampling loop
        
        # Generate sampling loop - diagnostic test
        
        
        # Generate sampling loop with timing measurement
        lines.extend([
            #"delay(10*ms)",
            #"self.core.wait_until_mu(now_mu())",
            #"self.core.break_realtime()",
            #"t_start_mu = self.core.get_rtio_counter_mu()",

            f"for i in range({self.numberOfSamples}):",
            "    with parallel:",
            f"        self.{self.device.name}.sample_mu(",
            f"            self.{self.dataString()}[i]",
            "        )",
            f"        delay({self.samplePeriod})",

            #"self.core.wait_until_mu(now_mu())",
            #"t_end_mu = self.core.get_rtio_counter_mu()",

            #'print("Sampler acquisition duration (s):", '
            #'self.core.mu_to_seconds(t_end_mu - t_start_mu))',
        ])




        # Apply 8 spaces to the top-level kernel statements
        return "\n" + "\n".join("        " + line for line in lines)


    
    def generateAnalyzeCode(self):
        if self.numberOfSamples > 0:

            # Convert GUI gain labels into numerical indices
            gain_indices = [
                GAIN_TO_MU[gain] for gain in self.gains
            ]

            return f"""
            full_scale = 20.48 if self.{self.device.name}.corrected_fs else 20.0
            gain_indices = {gain_indices!r}

            for i in range(8):
                # Convert raw ADC values into volts
                voltage = self.{self.dataString()}[:, i].astype(float) * (
                    full_scale / (65536.0 * (10 ** gain_indices[i]))
                )

                # Store voltage measurements
                self.set_dataset(
                    "{self.dataString()}_data_ch_" + str(i),
                    voltage
                )

            # Store requested sampling rate
            self.set_dataset(
                "{self.dataString()}_samplerate",
                {self.sampleRate:.3f}
            )"""

        return None


    def generateImportCode(self):
        return "import numpy as np"
