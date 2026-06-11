import gui.widgets.Design as Design
import gui.widgets.LabSetup.Port as Port
import PySide6.QtWidgets as QtW
import gui.crate as crate
import gui.widgets.Input as Input


class Config(Port.Config):
    def __init__(self, portName, listWidget):
        super(Config, self).__init__(portName, listWidget)

    def createParamWidgets(self):
        return Design.VBox()
    
    def createCalibrationWidgets(self):
        self.valueFields["hasAlmazny"] = Input.CheckBox(
            default=crate.LabSetup.get(self.name, "hasAlmazny"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "hasAlmazny", value
            ),
        )
        return Design.HBox(QtW.QLabel("hasAlmazny"), self.valueFields["hasAlmazny"], Design.Spacer())
