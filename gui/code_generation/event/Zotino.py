import gui.code_generation.hardware_util as hardware_util

from .Event import Event


class ZotinoEvent(Event):

    def __init__(self, time, duration, device, channels):
        """Sets the Voltages for multiple Zotino channels"""

        Event.__init__(self, time=time, duration=duration, device=device)
        self.priority = 5
        self.channels = channels
        self.variableName = self.device.generateVariableName("voltages")
        self.sweepVariableName = self.device.generateVariableName("sweep_voltages")
        self.stepTimeVariableName = self.device.generateVariableName("step_time")
        self.channelList = list(self.channels.keys())
        self.voltagesList = [self.channels[channel]["voltage"] for channel in self.channelList]
        self.sweepChannelList = [channel for channel in self.channelList if "sweep_voltage" in self.channels[channel]]
        self.stepCount = hardware_util.getZotinoStepCount(duration)
        self.stepTime = duration / self.stepCount
        self.sweepVoltagesList = [self.channels[channel]["sweep_voltage"] for channel in self.sweepChannelList]
        self.formulaList = [self.channels[channel]["formula_text"] for channel in self.sweepChannelList]
        self.sweepData = []
        for j in range(self.stepCount):
            self.sweepData.append([])
        for i in range(len(self.sweepChannelList)):
            voltage = self.voltagesList[self.channelList.index(self.sweepChannelList[i])]
            sweep_voltage = self.sweepVoltagesList[i]
            dataX, dataY = hardware_util.formulaTextToDataPoints(self.stepCount, self.formulaList[i])
            dataX, dataY = hardware_util.scaleFormulaData(dataX, dataY, duration, voltage, sweep_voltage)
            for j in range(self.stepCount):
                self.sweepData[j].append(dataY[j])

    def generateRunCode(self):
        code = f"""
        self.{self.device.name}.set_dac_mu(self.{self.variableName}, {[int(channel) for channel in self.channelList]})"""
        if len(self.sweepChannelList) > 0:
            code += f"""
        for i in range({self.stepCount}):
            delay_mu(self.{self.stepTimeVariableName})
            self.{self.device.name}.set_dac_mu(self.{self.sweepVariableName}[i], {[int(channel) for channel in self.sweepChannelList]})"""
        return code

    def generatePrepareCode(self):
        code = f"""
        self.{self.variableName} = [self.{self.device.name}.voltage_to_mu(voltage) for voltage in {self.voltagesList}]"""
        if len(self.sweepChannelList) > 0:
            code += f"""
        self.{self.sweepVariableName} = [[self.{self.device.name}.voltage_to_mu(voltage) for voltage in step] for step in {self.sweepData}]
        self.{self.stepTimeVariableName} = self.core.seconds_to_mu({self.stepTime})"""
        return code

    def getTimeCursorShift(self):
        if len(self.sweepChannelList) > 0:
            return self.stepTime * self.stepCount
        else:
            return 0
