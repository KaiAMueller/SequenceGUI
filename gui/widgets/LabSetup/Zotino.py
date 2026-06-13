import gui.widgets.LabSetup.DAC as DAC


class Config(DAC.Config):
    def __init__(self, portName, listWidget):
        super(Config, self).__init__(portName, listWidget)
