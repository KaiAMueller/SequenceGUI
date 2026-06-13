import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.LabSetup.Port as Port


class Config(Port.Config):
    def __init__(self, portName, listWidget):
        super(Config, self).__init__(portName, listWidget)

    def createCalibrationWidgets(self):
        self.valueFields["inverted"] = Input.CheckBox(
            default=crate.LabSetup.get(self.name, "inverted"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "inverted", value),
        )
        return Design.HBox(QtW.QLabel("inverted"), self.valueFields["inverted"], Design.Spacer())
