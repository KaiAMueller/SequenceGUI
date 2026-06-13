import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.LabSetup.Port as Port
import gui.widgets.PortState.DAC as PortstateDAC
import gui.widgets.Segment as Segment
import gui.widgets.SequenceEditor as SequenceEditor


def getAvailableChannels(device, currentChannel):
    channels = [str(i) for i in range(32)]
    for portName, portData in crate.labsetup.items():
        if not portData["isDir"]:
            if portData["device"] == device:
                c = str(portData["channel"])
                if c in channels and c != currentChannel:
                    channels.remove(c)
    return channels


class Config(Port.Config):
    def __init__(self, portName, listWidget, hasChannels=True, defaultUnit="V"):
        self.hasChannels = hasChannels
        self.defaultUnit = defaultUnit
        super(Config, self).__init__(portName, listWidget)

    def createParamWidgets(self):
        if self.hasChannels:
            self.valueFields["channel"] = Input.ComboBox(
                itemsGenerateFunction=lambda: getAvailableChannels(
                    crate.labsetup[self.name]["device"],
                    crate.labsetup[self.name]["channel"],
                ),
                default=crate.LabSetup.get(self.name, "channel"),
                changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "channel", value),
            )
        self.valueFields["calibration_enabled"] = Input.CheckBox(
            default=crate.LabSetup.get(self.name, "calibration_enabled"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "calibration_enabled", value),
        )
        self.valueFields["calibration_unit_text"] = Input.TextField(
            default=crate.LabSetup.get(self.name, "calibration_unit_text"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "calibration_unit_text", value),
        )
        self.valueFields["calibration_to_unit"] = Input.UnitCycler(
            units=[
                {"text": f"m{self.defaultUnit}", "factor": 1e-3},
                {"text": self.defaultUnit, "factor": 1},
            ],
            default=crate.LabSetup.get(self.name, "calibration_to_unit"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "calibration_to_unit", value),
        )
        self.valueFields["calibration_mode"] = Input.ComboBox(
            itemsGenerateFunction=lambda: ["Formula", "Dataset"],
            default=crate.LabSetup.get(self.name, "calibration_mode"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "calibration_mode", value),
        )
        self.valueFields["calibration_formula"] = Input.FormulaEditor(
            preText="U(x) = ",
            default=crate.LabSetup.get(self.name, "calibration_formula"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "calibration_formula", value),
        )
        self.valueFields["calibration_dataset"] = Input.DatasetEditor(
            text="Edit Calibration Dataset",
            dimensions=lambda: [
                crate.LabSetup.get(self.name, "calibration_unit_text"),
                crate.LabSetup.get(self.name, "calibration_to_unit")["text"],
            ],
            default=crate.LabSetup.get(self.name, "calibration_dataset"),
            changedCallback=lambda value: crate.LabSetup.ValueChange(self.name, "calibration_dataset", value),
        )

        self.calibrationWidgets = Design.VBox(
            Design.HBox(
                QtW.QLabel("Shown as"),
                Design.Spacer(),
                self.valueFields["calibration_unit_text"],
            ),
            Design.HBox(
                QtW.QLabel("To Unit"),
                Design.Spacer(),
                self.valueFields["calibration_to_unit"],
            ),
            Design.HBox(
                self.valueFields["calibration_mode"],
                Design.Spacer(),
                self.valueFields["calibration_formula"],
                self.valueFields["calibration_dataset"],
            ),
        )

        if not crate.LabSetup.get(self.name, "calibration_enabled"):
            self.updateCalibrationVisibility(False)
        self.updateCalibrationModeVisibility()

        return Design.VBox(
            (Design.HBox(QtW.QLabel("Channel"), 1, self.valueFields["channel"]) if self.hasChannels else None),
            Design.HBox(
                QtW.QLabel("Calibration"),
                Design.Spacer(),
                self.valueFields["calibration_enabled"],
            ),
            self.calibrationWidgets,
        )

    def updateCalibrationVisibility(self, enabled=None):
        if enabled is None:
            enabled = crate.LabSetup.get(self.name, "calibration_enabled")
        if enabled:
            self.calibrationWidgets.setVisible(True)
            self.updateCalibrationModeVisibility()
        else:
            self.calibrationWidgets.setVisible(False)

    def updateCalibrationModeVisibility(self, mode=None):
        if mode is None:
            mode = crate.LabSetup.get(self.name, "calibration_mode")
        if not crate.LabSetup.get(self.name, "calibration_enabled"):
            return
        if mode == "Formula":
            self.valueFields["calibration_formula"].setVisible(True)
            self.valueFields["calibration_dataset"].setVisible(False)
        elif mode == "Dataset":
            self.valueFields["calibration_formula"].setVisible(False)
            self.valueFields["calibration_dataset"].setVisible(True)

    def valueChange(self, valueName, value):
        super(Config, self).valueChange(valueName, value)
        if valueName == "calibration_enabled":
            self.updateCalibrationVisibility(value)
            self.updateAllUnitCyclersCalibrationUnit(value)
        elif valueName == "calibration_mode":
            self.updateCalibrationModeVisibility(value)

    def updateAllUnitCyclersCalibrationUnit(self, value):
        unitText = crate.LabSetup.get(self.name, "calibration_unit_text") if value else None
        if SequenceEditor.dock.configWidget is not None:
            for segment in SequenceEditor.dock.configWidget.segments():
                if type(segment) is Segment.PortStates:
                    for widget in segment.portStateWidgets.values():
                        if isinstance(widget, PortstateDAC.Widget):
                            widget.updateUnitCyclerCalibrationUnit(unitText)
