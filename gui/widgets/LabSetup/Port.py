import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.LabSetup as LabSetup
import gui.widgets.Viewer as Viewer


# ABSTRACT CLASS - OVERRIDDEN BY CLASSES FOR SPECIFIC MODULE, e.g. TTL, URUKUL...
class Config(Design.VBox):
    def __init__(self, name, labsetupWidget):
        self.validationConditions = {}

        # window
        self.name = name
        self.labsetupWidget = labsetupWidget

        self.jsonButton = Viewer.InfoButton(crate.labsetup[self.name])

        # device widget
        self.valueFields = {}
        self.valueFields["device"] = Input.ComboBox(
            itemsGenerateFunction=lambda: LabSetup.getDevices(crate.labsetup[self.name]),
            default=crate.labsetup[self.name]["device"],
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "device", value),
        )

        # layout
        super(Config, self).__init__(
            Design.HBox(QtW.QLabel("Device"), 1, self.valueFields["device"]),
            self.createParamWidgets(),
            self.createCalibrationWidgets(),
            Design.Spacer(),
            Design.HBox(Design.Spacer(), self.jsonButton),
        )

    def valueChange(self, valueName, value):
        if valueName in self.valueFields:
            self.valueFields[valueName].set(value)

    # abstract functions
    def createParamWidgets(self):
        return Design.VBox()

    def createCalibrationWidgets(self):
        return Design.VBox()
