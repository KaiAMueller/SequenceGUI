import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.PortState.PortState as PortState
import gui.widgets.Variables as Variables


class Widget(PortState.Widget):
    def __init__(self, segment, portName):
        super(Widget, self).__init__(segment, portName, ConfigDialog)

        # skip init checkbox
        self.configWidgets["skipInit"] = Input.ToggleButton(
            states=["Skip Init", "Init"],
            default=self.getValue("skipInit"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "skipInit",
                value,
            ),
        )

        # use Almazny Checkbox
        self.configWidgets["useAlmazny"] = Input.ToggleButton(
            states=["Almazny Used", "Almazny Disabled"],
            default=self.getValue("useAlmazny"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "useAlmazny",
                value,
            ),
        )

        # enable switch toggle
        self.configWidgets["switch_enable"] = Input.ToggleButton(
            states=["Set Switch", "Switch"],
            default=self.getValue("switch_enable"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "switch_enable",
                value,
            ),
        )

        # switch toggle
        self.configWidgets["switch"] = Input.ToggleButton(
            states=["ON", "OFF"],
            default=self.getValue("switch"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "switch",
                value,
            ),
        )

        # enable frequency update checkbox
        self.configWidgets["freq_enable"] = Input.ToggleButton(
            states=["Set Frequency", "Frequency"],
            default=self.getValue("freq_enable"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "freq_enable",
                value,
            ),
        )

        # frequency field
        self.configWidgets["freq"] = Input.UnitValueField(
            default=self.getValue("freq"),
            allowedUnits=[
                {"text": "MHz", "factor": 1e6},
                {"text": "GHz", "factor": 1e9},
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

        # attenuation enable checkbox
        self.configWidgets["attenuation_enable"] = Input.ToggleButton(
            states=["Set Attenuation", "Attenuation"],
            default=self.getValue("attenuation_enable"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "attenuation_enable",
                value,
            ),
        )

        # attenuation field
        self.configWidgets["attenuation"] = Input.UnitValueField(
            default=self.getValue("attenuation"),
            allowedUnits=[
                {"text": "dB", "factor": 1},
            ],
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "attenuation",
                value,
            ),
        )

        self.updatePreviewWidget()

    def updatePreviewWidget(self):
        text = generatePreviewText(self.getData())
        self.previewWidget.setText(text)

    def valueChange(self, valueName, newValue):
        super(Widget, self).valueChange(valueName, newValue)
        if valueName in ["switch_enable", "attenuation_enable", "freq_enable"]:
            self.segment.sequence.alignPorts()

    def getTableViewInfo(self):
        return getTableViewInfo(self.getData())


def getTableViewInfo(data):
    tv = {
        "text": generatePreviewText(data),
        "color": (0, 1, 0) if data["switch_enable"] and data["switch"] else (0, 0, 0),
    }
    tv["next_text"] = tv["text"]
    tv["next_color"] = tv["color"]
    return tv



def generatePreviewText(data):
    switch_enable = data["switch_enable"]
    attenuation_enable = data["attenuation_enable"]
    freq_enable = data["freq_enable"]
    text = ""
    if switch_enable:
        switch = data["switch"]
        text += ("ON" if switch else "OFF") + "\n"
    if attenuation_enable:
        attenuation = data["attenuation"]
        text += util.unitValueToText(attenuation) + "\n"
    if freq_enable:
        freq = data["freq"]
        text += util.unitValueToText(freq) + "\n"
    return text[:-1] if text != "" else "empty"


class ConfigDialog(PortState.ConfigDialog):
    def __init__(self, portStateWidget):
        self.almaznyWarningLabel = Design.Button("⚠️")
        self.almaznyWarningLabel.setEnabled(False)
        self.almaznyWarningLabel.setToolTip("Make sure the Almazny Ports are connected")
        super(ConfigDialog, self).__init__(portStateWidget)

    def generateConfigurationWidgets(self):
        return Design.Grid(
            [
                [self.configWidgets["skipInit"], QtW.QWidget()],
                ([self.configWidgets["useAlmazny"], self.almaznyWarningLabel] if crate.LabSetup.get(self.portName, "hasAlmazny") else [QtW.QWidget(), QtW.QWidget()]),
                [self.configWidgets["switch_enable"], self.configWidgets["switch"]],
                [self.configWidgets["freq_enable"], self.configWidgets["freq"]],
                [
                    self.configWidgets["attenuation_enable"],
                    self.configWidgets["attenuation"],
                ],
            ],
            alignment=QtC.Qt.AlignmentFlag.AlignLeft,
        )

    def updateVisibility(self):
        if self.isAboutToClose:
            return
        self.configWidgets["switch_enable"].setVisible(True)
        self.configWidgets["freq_enable"].setVisible(True)
        self.configWidgets["attenuation_enable"].setVisible(True)
        switch_enable = self.configWidgets["switch_enable"].get()
        freq_enable = self.configWidgets["freq_enable"].get()
        attenuation_enable = self.configWidgets["attenuation_enable"].get()
        self.configWidgets["switch"].setVisible(switch_enable)
        self.configWidgets["freq"].setVisible(freq_enable)
        self.configWidgets["attenuation"].setVisible(attenuation_enable)
        if crate.LabSetup.get(self.portName, "hasAlmazny"):
            if self.configWidgets["useAlmazny"].get():
                self.almaznyWarningLabel.setText("⚠️")
            else:
                self.almaznyWarningLabel.setText(" ")
