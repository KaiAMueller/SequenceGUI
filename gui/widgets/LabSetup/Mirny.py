import gui.widgets.Design as Design
import gui.widgets.LabSetup.Port as Port


class Config(Port.Config):
    def __init__(self, portName, listWidget):
        super(Config, self).__init__(portName, listWidget)

    def createParamWidgets(self):
        return Design.VBox()
