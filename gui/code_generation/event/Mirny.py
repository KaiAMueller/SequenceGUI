from numpy import int32

from .Event import Event


class MirnyEvent(Event):

    def __init__(
        self,
        time,
        duration,
        device,
        switch,
        freq,
        attenuation,
        skipInit,
        useAlmazny,
        almaznyDeviceName,
    ):
        super(MirnyEvent, self).__init__(time=time, duration=duration, device=device)
        self.switch = switch
        self.freq = freq
        self.attenuation = attenuation
        self.useAlmazny = useAlmazny
        self.almaznyDeviceName = almaznyDeviceName
        self.channel = device.name[-1]
        if skipInit:
            self.device.cpld.skipInit = True
        if useAlmazny:
            a = self.attenuation is not None
            s = self.switch is not None
            assert not (a ^ s), "Almazny attenuation and switch must be set together"

    def generateRunCode(self):
        code = ""
        if not self.useAlmazny:
            if self.attenuation is not None:
                code += f"""
        self.{self.device.name}.set_att_mu({int32(255) - int32(round(self.attenuation * 8))}) # machine unit for {self.attenuation} dB"""

            if self.freq is not None:
                code += f"""
        self.{self.device.name}.set_frequency({self.freq})"""

            if self.switch is not None and (self.device.enabled is None or self.switch ^ self.device.enabled):
                self.device.enabled = self.switch
                code += f"""
        self.{self.device.name}.sw.{"on" if self.switch else "off"}()"""

        else:
            if self.freq is not None:
                code += f"""
        self.{self.device.name}.set_frequency({0.25 * self.freq})"""

            if self.attenuation is not None:
                code += f"""
        self.{self.almaznyDeviceName}.set_att({self.channel}, {self.attenuation}, {self.switch})
        self.{self.almaznyDeviceName}.output_toggle(True)"""
        return code

    def generatePrepareCode(self):
        return None
