import gui.code_generation.hardware_util as hardware_util

from .Event import Event


class FastinoEvent(Event):

    # def __init__(self, time, duration, device, channels, voltages):
    def __init__(self, time, duration, device, channels):
        """Sets the Voltages for multiple Fastino channels"""

        Event.__init__(self, time=time, duration=duration, device=device)
        self.priority = 6
        self.channels = channels
        self.variableName = self.device.generateVariableName("voltages")
        self.sweepVariableName = self.device.generateVariableName("sweep_voltages")
        self.datasetVariableName = self.device.generateVariableName("dataset_voltages")
        self.channelRotateStepTimeVariableName = self.device.generateVariableName("rotate_chanel_time")
        self.channelRotateSingleTimeVariableName = self.device.generateVariableName("single_time")
        self.channelList = list(self.channels.keys())
        self.voltagesList = [self.channels[channel]["voltage"] for channel in self.channelList]
        self.sweepChannelList = [channel for channel in self.channelList if "sweep_voltage" in self.channels[channel]]
        self.datasetChannelList = [channel for channel in self.channelList if "loaded_dataset" in self.channels[channel]]
        self.stepCount = hardware_util.getFastinoStepCount(duration, parallel_channels=max(1, len(self.sweepChannelList)))
        self.loaded_datasetList=[self.channels[channel]["loaded_dataset"] for channel in self.datasetChannelList]
        #Adjust stepCount to the dataset step count
        if self.loaded_datasetList:
            assert  self.stepCount > len(self.loaded_datasetList[0]['x']), "Too many points in dataset (Fastino)"
            self.stepCount=len(self.loaded_datasetList[0]['x'])
        self.channelRotateSingleTime = 5e-8
        self.stepTime = (duration - self.channelRotateSingleTime * len(self.channelList))/ self.stepCount
        self.channelRotateStepTime = self.stepTime / (len(self.sweepChannelList) + len(self.datasetChannelList)) if (len(self.sweepChannelList) + len(self.datasetChannelList)) > 0 else 0
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
    
        self.loadedData = []
        for j in range(self.stepCount):
            self.loadedData.append([])
        for i in range(len(self.loaded_datasetList)):
            dataY = self.loaded_datasetList[i]['y']
            for j in range(self.stepCount):
                self.loadedData[j].append(dataY[j])

                

        


    def generateRunCode(self):
        code = ""
        for i in range(len(self.channelList)):
            channel = self.channelList[i]
            code += f"""
        self.{self.device.name}.set_dac_mu({int(channel)}, self.{self.variableName}[{i}])
        delay_mu(self.{self.channelRotateSingleTimeVariableName})"""
        if len(self.sweepChannelList) > 0:
            code += f"""
        for i in range({self.stepCount}):"""
        for i in range(len(self.sweepChannelList)):
            sweepChannel = self.sweepChannelList[i]
            code += f"""
            delay_mu(self.{self.channelRotateStepTimeVariableName})
            self.{self.device.name}.set_dac_mu({int(sweepChannel)}, self.{self.sweepVariableName}[i][{i}])"""
        if len(self.sweepChannelList) == 0 and not len(self.datasetChannelList) == 0:
            code += f"""
        for i in range({self.stepCount}):"""
        for i in range(len(self.datasetChannelList)):
            datasetChannel = self.datasetChannelList[i]
            code += f"""
            delay_mu(self.{self.channelRotateStepTimeVariableName})
            self.{self.device.name}.set_dac_mu({int(datasetChannel)}, self.{self.datasetVariableName}[i][{i}])"""
        return code

    def generatePrepareCode(self):
        code = f"""
        self.{self.variableName} = [self.{self.device.name}.voltage_to_mu(voltage) for voltage in {self.voltagesList}]
        self.{self.channelRotateSingleTimeVariableName} = self.core.seconds_to_mu({self.channelRotateSingleTime})"""
        if len(self.sweepChannelList) > 0:
            code += f"""
        self.{self.sweepVariableName} = [[self.{self.device.name}.voltage_to_mu(voltage) for voltage in step] for step in {self.sweepData}]"""
        if len(self.sweepChannelList) > 0 or len(self.loaded_datasetList) > 0:
            code += f"""
        self.{self.channelRotateStepTimeVariableName} = self.core.seconds_to_mu({self.channelRotateStepTime})"""
        if len(self.loaded_datasetList) > 0:
            code+= f'''
        self.{self.datasetVariableName} = [[self.{self.device.name}.voltage_to_mu(voltage) for voltage in step] for step in {self.loadedData}]
        '''
        return code

    def getTimeCursorShift(self):
        if len(self.sweepChannelList) > 0:
            return self.stepTime * self.stepCount
        else:
            return 0
