import gui.code_generation.hardware_util as hardware_util

from .Event import Event


class CurrentDriverEvent(Event):  # For the CurrentDriver 1V on DAC will output 1A... so using either unit is fine in this code... in front-end the user can use the calibration feature as well
    def __init__(self, time, duration, device, voltage, sweep_voltage=None, formula_text=None):
        super(CurrentDriverEvent, self).__init__(time=time, duration=duration, device=device)
        self.voltage = voltage
        self.sweep_voltage = sweep_voltage
        self.voltageVariableName = self.device.generateVariableName("voltage")
        self.sweepVariableName = self.device.generateVariableName("sweep_voltage")
        self.stepTimeVariableName = self.device.generateVariableName("step_time")
        self.stepCount = hardware_util.getCurrentDriverStepCount(duration)
        self.stepTime = duration / self.stepCount - 528e-9  # 528 ns because 125 MHz RTIO Clock, divided by 2 -> 62.5 MHz -> 16ns per step, -> times 33 steps is 528 ns
        assert self.stepTime > -1e-9, "CurrentDriver Error: Step time too small, you may need to increase the duration."
        self.stepTime = max(self.stepTime, 0)
        self.sweepData = []
        if self.sweep_voltage is not None:
            dataX, dataY = hardware_util.formulaTextToDataPoints(self.stepCount, formula_text)
            dataX, dataY = hardware_util.scaleFormulaData(dataX, dataY, duration, voltage, sweep_voltage)
            for j in range(self.stepCount):
                self.sweepData.append(dataY[j])

    def generateImportCode(self):
        return """
CURRENT_DRIVER_SPI_CONFIG = (0*spi.SPI_OFFLINE | 0*spi.SPI_END |
            0*spi.SPI_INPUT | 0*spi.SPI_CS_POLARITY |
            0*spi.SPI_CLK_POLARITY | 1*spi.SPI_CLK_PHASE |
            0*spi.SPI_LSB_FIRST | 0*spi.SPI_HALF_DUPLEX)
            
class CurrentDriverHandler:
    def __init__(self, spi):
        self.spi = spi
    
    def voltage_to_mu(self, voltage):
        voltage_bits = int(2**20/20*(voltage+10))
        bits = np.int32(0 << 31 | 1 << 24 | voltage_bits << 4)
        return bits

    @kernel
    def set_voltage_mu(self, voltage_mu):
        self.spi.set_config_mu(CURRENT_DRIVER_SPI_CONFIG | spi.SPI_END, 32, 2, 1)
        self.spi.write(voltage_mu)
"""

    def generateRunCode(self):
        if self.sweep_voltage is not None:
            code = f"""
        for i in range({self.stepCount}):
            self.{self.device.handlerVariableName}.set_voltage_mu(self.{self.sweepVariableName}[i])
            delay_mu(self.{self.stepTimeVariableName})"""
        else:
            code = f"""
        self.{self.device.handlerVariableName}.set_voltage_mu(self.{self.voltageVariableName})"""
        return code

    def generatePrepareCode(self):
        if self.sweep_voltage is not None:
            code = f"""
        self.{self.sweepVariableName} = [self.{self.device.handlerVariableName}.voltage_to_mu(voltage) for voltage in {self.sweepData}]
        self.{self.stepTimeVariableName} = self.core.seconds_to_mu({self.stepTime})"""
        else:
            code = f"""
        self.{self.voltageVariableName} = self.{self.device.handlerVariableName}.voltage_to_mu({self.voltage})"""
        return code
