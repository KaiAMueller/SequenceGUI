import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.PortState.PortState as PortState


class Widget(PortState.Widget):
    def __init__(self, segment, portName):
        super(Widget, self).__init__(segment, portName, ConfigDialog)

        self.configWidgets["state"] = Input.ToggleButton(
            default=self.getValue("state"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "state",
                value,
            ),
        )
        self.updatePreviewWidget()

    def generatePreviewWidget(self):
        widget = Design.Button("not implemented", flat=False, size="medium")
        widget.clicked.connect(self.toggleState)
        widget.onRightClick = self.openConfigButtonClicked
        widget.setCheckable(True)
        return widget

    def updatePreviewWidget(self):
        state = self.getValue("state")
        self.previewWidget.setText("ON" if state else "OFF")
        self.previewWidget.setChecked(state)

    def toggleState(self):
        state = self.getValue("state")
        crate.Sequences.PortStateValueChange(
            self.segment.sequence.name,
            self.segment.name,
            self.portName,
            "state",
            not state,
        )

    def getTableViewInfo(self):
        return getTableViewInfo(self.getData())


def getTableViewInfo(data):
    tv = {
        "text": "ON" if data["state"] else "OFF",
        "color": (0, 1, 0) if data["state"] else (0, 0, 0),
    }
    tv["next_text"] = tv["text"]
    tv["next_color"] = tv["color"]
    return tv


class ConfigDialog(PortState.ConfigDialog):
    def __init__(self, portStateWidget):
        super(ConfigDialog, self).__init__(portStateWidget)
        # portStateWidget.updatePreviewWidget()

    def generateConfigurationWidgets(self):
        return Design.VBox(
            Design.HBox(QtW.QLabel("State"), Design.Spacer(), self.configWidgets["state"]),
        )
