import gui.settings as settings

from .Device import Device


class Fastino(Device):
    def __init__(self, name):
        super().__init__(name)

    def generateInitCode(self):
        code = f"""
        self.{self.name}.init()"""
        if settings.getFastinoAfePwrOff():
            code += f"""
        delay(2*us)
        self.{self.name}.set_cfg(reset=0, afe_power_down=1, dac_clr=0, clr_err=0)
        delay(2*us)"""
        return code
