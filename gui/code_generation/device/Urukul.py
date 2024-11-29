from .Device import Device


class Urukul(Device):

    def __init__(self, name, cpld):
        super().__init__(name, [cpld])
        self.enabled = None
        self.need_init = False
        self.channel = int(name.split("ch")[-1])
        self.state = "normal"
        self.last_sweep_dir = "down"
        self.cpld = cpld
        self.cpld.addChannel(self)
        self.ramEvents = []

        self.functions.append(
            """
    @kernel
    def write_ram(self, device, data):
        device.bus.set_config_mu(urukul.SPI_CONFIG, 8, urukul.SPIT_DDS_WR, device.chip_select)
        device.bus.write(_AD9910_REG_RAM << 24)
        device.bus.set_config_mu(urukul.SPI_CONFIG, 32, urukul.SPIT_DDS_WR, device.chip_select)
        for i in range(len(data) - 1):
            device.bus.write(data[i])
        device.bus.set_config_mu(urukul.SPI_CONFIG | spi.SPI_END, 32, urukul.SPIT_DDS_WR, device.chip_select)
        device.bus.write(data[len(data) - 1])"""
        )

    def generateInitCode(self):
        code = (
            f"""
        self.{self.name}.init()
        delay(1 * ms)"""
            if self.need_init
            else ""
        )
        return code

    def addRamEvent(self, ramEvent):
        self.ramEvents.append(ramEvent)

    def needInit(self):
        self.need_init = True


class UrukulCPLD(Device):
    def __init__(self, name):
        super().__init__(name)
        self.priority = 20
        self.channels = []
        self.need_init = False
        self.need_get_att = False

    def addChannel(self, channel):
        if channel not in self.channels:
            self.channels.append(channel)

    def needInit(self):
        self.need_init = True

    def needGetAtt(self):
        self.need_get_att = True

    def generateInitCode(self):
        code = ""
        if self.need_init:
            code += f"""
        self.{self.name}.init()
        delay(1 * ms)"""
        if self.need_get_att:
            code += f"""
        self.{self.name}.get_att_mu()
        delay(1 * ms)"""
        return code
