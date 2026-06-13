import numpy as np

from .Event import Event


class UrukulEvent(Event):

    def __init__(self, time, duration, device, amp, freq, phase, switch, attenuation):
        super(UrukulEvent, self).__init__(time=time, duration=duration, device=device)
        self.amp = amp
        self.freq = freq
        self.phase = phase
        self.switch = switch
        self.attenuation = attenuation
        self.variableNameAmp = self.device.generateVariableName("amp") if self.amp is not None else None
        self.variableNameFreq = self.device.generateVariableName("freq") if self.freq is not None else None
        self.variableNamePhase = self.device.generateVariableName("phase") if self.phase is not None else None
        if self.amp is not None or self.freq is not None:
            self.device.needInit()
            self.device.cpld.needInit()
        if self.attenuation is not None:
            self.device.cpld.needGetAtt()

    def clone(self):
        return type(self)(
            time=self.time,
            duration=self.duration,
            device=self.device,
            amp=self.amp,
            freq=self.freq,
            attenuation=self.attenuation,
            switch=self.switch,
        )

    def generateRunCode(self):
        code = ""
        code += self.generateSetAttCode()
        code += self.generateSetFreqAmpCode(setNormalState=True)
        code += self.generateSetSwitchCode()
        return code

    def generateResetCfrCode(self):
        code = ""
        if self.device.state == "sweep":
            code += f"""
        self.{self.device.name}.set_cfr2()"""
        elif self.device.state == "ram":
            code += f"""
        self.{self.device.name}.set_cfr1()"""
        return code

    def generateSetAttCode(self):
        code = ""
        if self.attenuation is not None:
            code += f"""
        self.{self.device.name}.set_att({self.attenuation}*dB)"""
        return code

    def generateSetFreqAmpCode(self, setNormalState=False):
        code = ""
        if self.variableNameAmp is not None and self.variableNameFreq is not None:
            code += self.generateSetMaskNuCode()
            code += self.generateResetCfrCode()
            if setNormalState:
                self.device.state = "normal"
        if self.variableNameFreq is not None:
            if self.variableNamePhase is not None:
                code += f"""
        self.{self.device.name}.set_mu(self.{self.variableNameFreq}, pow_=self.{self.variableNamePhase}, asf=self.{self.variableNameAmp})"""
            else:
                code += f"""
        self.{self.device.name}.set_mu(self.{self.variableNameFreq}, asf=self.{self.variableNameAmp})"""
        return code

    def generateSetSwitchCode(self):
        code = ""
        if self.switch is not None:
            code += f"""
        self.{self.device.name}.sw.{"on" if self.switch else "off"}()"""
        return code

    def generateSetMaskNuCode(self):
        code = f"""
        cpld = self.{self.device.name}.cpld
        cpld.cfg_write((cpld.cfg_reg | (15 << urukul.CFG_MASK_NU)) & ~(1 << urukul.CFG_MASK_NU + {self.device.channel}))"""
        return code

    def generatePrepareCode(self):
        code = ""
        if self.freq is not None:
            code += f"""
        self.{self.variableNameFreq} = self.{self.device.name}.frequency_to_ftw({self.freq})"""
        if self.amp is not None:
            code += f"""
        self.{self.variableNameAmp} = self.{self.device.name}.amplitude_to_asf({self.amp})"""
        if self.phase is not None:
            code += f"""
        self.{self.variableNamePhase} = self.{self.device.name}.turns_to_pow({self.phase})"""
        return code

    def generateImportCode(self):
        return "from artiq.coredevice import ad9910, urukul"


class UrukulRamEvent(UrukulEvent):
    """
    If step_count is its maximum 1024, it needs around 560 us to load the RAM.
    """

    def __init__(
        self,
        time,
        duration,
        device,
        switch,
        amp,
        freq,
        phase,
        attenuation,
        only_execute,
        ram_amplitude_formula,
        ram_phase_formula,
        ram_frequency_formula,
        ram_profile,
        ram_start,
        ram_end,
        ram_step_size,
        ram_destination,
        ram_mode,
    ):
        super(UrukulRamEvent, self).__init__(
            time=time,
            duration=duration,
            device=device,
            switch=switch,
            freq=freq,
            amp=amp,
            phase=phase,
            attenuation=attenuation,
        )
        self.only_execute = only_execute
        self.ram_amplitude_formula = ram_amplitude_formula
        self.ram_phase_formula = ram_phase_formula
        self.ram_frequency_formula = ram_frequency_formula
        self.ram_profile = ram_profile
        self.ram_start = ram_start
        self.ram_end = ram_end
        self.ram_step_size = ram_step_size
        self.ram_destination = ram_destination
        self.ram_mode = ram_mode
        self.ram_destination = ram_destination
        self.step_count = (int(self.ram_end) - int(self.ram_start) + 1) if self.ram_start is not None else None
        self.variable_name_ram_data = self.device.generateVariableName("ramdata")
        self.device.addRamEvent(self)

    def generatePrepareCode(self):
        if self.only_execute:
            return ""
        code = (
            super(UrukulRamEvent, self).generatePrepareCode()
            + f"""
        ram_amp_data = [0]*{self.step_count}
        ram_phase_data = [0]*{self.step_count}
        ram_frequency_data = [0]*{self.step_count}
        self.{self.variable_name_ram_data} = np.array(np.zeros({self.step_count}), dtype=np.int32)
        for i in range({self.step_count}):
            x = i / {self.step_count}"""
        )
        if self.ram_destination == "RAM_DEST_ASF":
            code += f"""
            ram_amp_data[i] = min(1.0, max(0.0, {self.ram_amplitude_formula}))
        self.{self.device.name}.amplitude_to_ram(ram_amp_data, self.{self.variable_name_ram_data})
            """
        if self.ram_destination == "RAM_DEST_POW":
            code += f"""
            ram_phase_data[i] = {self.ram_phase_formula}
        self.{self.device.name}.turns_to_ram(ram_phase_data, self.{self.variable_name_ram_data})
            """
        if self.ram_destination == "RAM_DEST_FTW":
            code += f"""
            ram_frequency_data[i] = {self.ram_frequency_formula}
        self.{self.device.name}.frequency_to_ram(ram_frequency_data, self.{self.variable_name_ram_data})
            """
        if self.ram_destination == "RAM_DEST_POWASF":
            code += f"""
            ram_amp_data[i] = min(1.0, max(0.0, {self.ram_amplitude_formula}))
            ram_phase_data[i] = {self.ram_phase_formula}
        self.{self.device.name}.turns_amplitude_to_ram(ram_phase_data, ram_amp_data, self.{self.variable_name_ram_data})
            """
        return code

    def generateRunCode(self):
        code = ""
        code += self.generateSetAttCode()
        code += self.generateSetSwitchCode()
        code += self.generateSetMaskNuCode()
        if self.device.state == "sweep":
            code += f"""
        self.{self.device.name}.set_cfr2()"""
            
        if self.only_execute:
            code += f"""
        self.{self.device.cpld.name}.set_profile({self.ram_profile})
        self.{self.device.cpld.name}.io_update.pulse_mu(8)
        """
        else:
            code += f"""
        self.{self.device.cpld.name}.set_profile({self.ram_profile})
        self.{self.device.name}.set_ftw(self.{self.variableNameFreq})
        self.{self.device.name}.set_cfr1()
        self.{self.device.cpld.name}.io_update.pulse_mu(8)
        self.{self.device.name}.set_profile_ram(
            start={self.ram_start},
            end={self.ram_end},
            step={self.ram_step_size},
            profile={self.ram_profile},
            mode={self.ram_mode}
            )
        self.{self.device.cpld.name}.io_update.pulse_mu(8)
        self.write_ram(self.{self.device.name}, self.{self.variable_name_ram_data})
        self.{self.device.name}.set_cfr1(ram_enable=1, ram_destination={self.ram_destination}, phase_autoclear=1)
        """
        self.device.state = "ram"
        return code


class UrukulSweepEvent(UrukulEvent):
    def __init__(
        self,
        time,
        duration,
        device,
        switch,
        amp,
        freq,
        attenuation,
        sweep_duration,
        sweep_freq = None,
        sweep_amp = None,
    ):
        super(UrukulSweepEvent, self).__init__(
            time=time,
            duration=duration,
            device=device,
            amp=amp,
            freq=freq,
            switch=switch,
            attenuation=attenuation,
            phase=None,
        )
        self.variableNameSweepFreq = self.device.generateVariableName("sweep_freq")
        self.sweep_freq = sweep_freq
        self.sweep_amp = sweep_amp
        self.sweep_duration = sweep_duration if sweep_duration != None else duration

    def clone(self):
        raise NotImplementedError

    def generateResetCfrCode(self):
        code = ""
        if self.device.state == "ram":
            code += f"""
        self.{self.device.name}.set_cfr1()"""
        return code

    
    def generateRunCode(self):
        code = ""
        code += self.generateSetAttCode()
        code += self.generateSetFreqAmpCode()

        current_dir = "down" if (self.sweep_freq is not None and self.sweep_freq < self.freq) or (self.sweep_amp is not None and self.sweep_amp < self.amp) else "up"

        if current_dir == self.device.last_sweep_dir:
            code += f"""
        self.{self.device.name}.write32(ad9910._AD9910_REG_CFR1,1 << 12)
        self.{self.device.name}.cpld.io_update.pulse_mu(8)
        self.{self.device.name}.set_cfr1()
        self.{self.device.name}.set_cfr2()
        self.{self.device.name}.cpld.io_update.pulse_mu(8)"""
        if self.sweep_freq is not None:
            (
                upper_limit,
                lower_limit,
                ramp_rate,
                decrement_step_size,
                increment_step_size,
            ) = self.generateSweepFrequencyParameters()
            code += f"""
        delay(10*us)
        self.{self.device.name}.write32(ad9910._AD9910_REG_CFR2,0x01010000|(0<<20)|(1<<19)|(3<<17)|(1<<7))"""

        elif self.sweep_amp is not None:
            (
                upper_limit,
                lower_limit,
                ramp_rate,
                decrement_step_size,
                increment_step_size,
            ) = self.generateSweepAmplitudeParameters()
            #Bit 21 is for amplitude
            code += f"""
        delay(10*us)
        self.{self.device.name}.write32(ad9910._AD9910_REG_CFR2,(1<<21)|(1 << 19)|(3<<17)|(1<<7))"""

        code += f"""
        self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_LIMIT, {upper_limit}, {lower_limit})
        self.{self.device.name}.write32(ad9910._AD9910_REG_RAMP_RATE, {ramp_rate})
        self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_STEP, {decrement_step_size}, {increment_step_size})
        self.{self.device.name}.cpld.io_update.pulse_mu(8)"""

        if current_dir == "down":
            code += f"""
        self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_STEP, {decrement_step_size}, 0)
        self.{self.device.name}.cpld.io_update.pulse_mu(8)"""
            
        # current_dir = "down" if (self.sweep_freq is not None and self.sweep_freq < self.freq) or (self.sweep_amp is not None and self.sweep_amp < self.amp) else "up"
        # if current_dir == "down":
        #     if self.device.last_sweep_dir == "down":
        #         code += f"""
        # self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_STEP, 0, (1 << 31))
        # self.{self.device.name}.cpld.io_update.pulse_mu(8)"""
        #     code += f"""
        # self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_STEP, {decrement_step_size}, 0)
        # self.{self.device.name}.cpld.io_update.pulse_mu(8)"""
        # else:
        #     if self.device.last_sweep_dir == "up":
        #         code += f"""
        # self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_STEP, (1 << 31), 0)
        # self.{self.device.name}.cpld.io_update.pulse_mu(8)"""
        #     code += f"""
        # self.{self.device.name}.write64(ad9910._AD9910_REG_RAMP_STEP, 0, {increment_step_size})
        # self.{self.device.name}.cpld.io_update.pulse_mu(8)"""

        self.device.last_sweep_dir = current_dir
        self.device.state = "sweep"
        code += self.generateSetSwitchCode()
        return code

    def generateSweepFrequencyParameters(self):

        ftwPerHz = (1 << 32) / (1e9)
        freq_mu = int(self.freq * ftwPerHz)
        sweep_freq_mu = int(self.sweep_freq * ftwPerHz)
        freq_diff_mu = abs(freq_mu - sweep_freq_mu)
        duration_mu = int(self.sweep_duration / 4e-9)  # 4ns is one step

        ramp_rate = min((1 << 16) - 1, int(np.ceil(duration_mu / 1000)))  # check if ramp rate is too high for 16 bits. 1000 steps should be enough for a smooth ramp
        steps = int(np.ceil(duration_mu / ramp_rate))
        freq_step_size = int(np.ceil(freq_diff_mu / steps))

        if self.sweep_freq > self.freq:
            return sweep_freq_mu, freq_mu, ramp_rate, 0, freq_step_size
        else:
            return freq_mu, sweep_freq_mu, (ramp_rate << 16), freq_step_size, (1 << 31)
    
    def generateSweepAmplitudeParameters(self):

        amp_mu = int(round(self.amp * 0x3fff))
        sweep_amp_mu = int(round(self.sweep_amp * 0x3fff))
        amp_diff_mu = abs(amp_mu - sweep_amp_mu)
        duration_mu = int(self.sweep_duration / 4e-9)  # 4ns is one step

        ramp_rate = min((1 << 16) - 1, int(np.ceil(duration_mu / 1000)))  # check if ramp rate is too high for 16 bits. 1000 steps should be enough for a smooth ramp
        steps = int(np.ceil(duration_mu / ramp_rate))
        amp_step_size = int(np.ceil(amp_diff_mu / steps))

        if self.sweep_amp > self.amp:
            return (sweep_amp_mu << 18), (amp_mu << 18), ramp_rate, 0, (amp_step_size << 18)
        else:
            return (amp_mu << 18), (sweep_amp_mu << 18), (ramp_rate << 16), (amp_step_size << 18), (1 << 31)
                
