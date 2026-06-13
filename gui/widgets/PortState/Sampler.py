import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.PortState.PortState as PortState
import gui.widgets.Variables as Variables


class Widget(PortState.Widget):
    def __init__(self, segment, portName):
        super(Widget, self).__init__(segment, portName, ConfigDialog)

        # frequency field
        self.configWidgets["freq"] = Input.UnitValueField(
            default=self.getValue("freq"),
            allowedUnits=[
                {"text": "Hz", "factor": 1},
                {"text": "kHz", "factor": 1e3},
                {"text": "MHz", "factor": 1e6},
            ],
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "freq",
                value,
            ),
        )
        self.updatePreviewWidget()

    def updatePreviewWidget(self):
        freq = self.getValue("freq")
        self.previewWidget.setText(freq["text"] + " " + freq["unit"]["text"])

    def getTableViewInfo(self):
        return getTableViewInfo(self.getData())


def getTableViewInfo(data):
    return {
        "text": "SAMPLE",
        "color": (0, 0, 1),
    }


class ConfigDialog(PortState.ConfigDialog):
    def __init__(self, portStateWidget):
        super(ConfigDialog, self).__init__(portStateWidget)

    def generateConfigurationWidgets(self):
        return Design.VBox(
            Design.HBox(QtW.QLabel("Sample Rate"), Design.Spacer(), self.configWidgets["freq"]),
        )
