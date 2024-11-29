import traceback

import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.code_generation.hardware_util as hardware_util
import gui.crate as crate
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Formula as Formula
import gui.widgets.Input as Input
import gui.widgets.PortState.PortState as PortState
import gui.widgets.Variables as Variables


class Widget(PortState.Widget):
    def __init__(self, segment, portName, defaultUnit="V"):
        self.defaultUnit = defaultUnit
        super(Widget, self).__init__(segment, portName, ConfigDialog)

        allowedUnits = [
            {"text": f"m{self.defaultUnit}", "factor": 1e-3},
            {"text": self.defaultUnit, "factor": 1},
        ]
        if crate.LabSetup.get(portName, "calibration_enabled"):
            allowedUnits.append(
                {
                    "text": crate.LabSetup.get(portName, "calibration_unit_text"),
                    "factor": 1,
                }
            )

        # voltage field
        self.configWidgets["voltage"] = Input.UnitValueField(
            default=self.getValue("voltage"),
            allowedUnits=allowedUnits,
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "voltage",
                value,
            ),
        )

        # sweep enable checkbox
        self.configWidgets["sweep_enable"] = Input.CheckBox(
            text="Sweep to",
            default=self.getValue("sweep_enable"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "sweep_enable",
                value,
            ),
        )

        # sweep voltage field
        self.configWidgets["sweep_voltage"] = Input.UnitValueField(
            default=self.getValue("sweep_voltage"),
            allowedUnits=allowedUnits,
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "sweep_voltage",
                value,
            ),
        )

        # sweep formula enable checkbox
        self.configWidgets["formula_enable"] = Input.CheckBox(
            text="Formula",
            default=self.getValue("formula_enable"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "formula_enable",
                value,
            ),
        )

        # formula selection dialog button
        self.configWidgets["formula_selection_button"] = Formula.SelectionButton(
            text="📚",
            callback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "formula_text",
                value,
            ),
        )

        # sweep formula field
        self.configWidgets["formula_text"] = Input.FormulaField(
            text="Set Formula f(x) = ",
            default=self.getValue("formula_text"),
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "formula_text",
                value,
            ),
        )

        self.updatePreviewWidget()

    def getFormulaSelection(self):
        return ["Gauss", "Custom"]

    def updatePreviewWidget(self):
        voltage = self.getValue("voltage")
        sweep_enable = self.getValue("sweep_enable")
        if sweep_enable:
            sweep_voltage = self.getValue("sweep_voltage")
            arrow = " ↗ " if Input.getValueFromState(voltage, replacer=Variables.replacer) < Input.getValueFromState(sweep_voltage, replacer=Variables.replacer) else " ↘ "
            if voltage["unit"] == sweep_voltage["unit"]:
                self.previewWidget.setText(voltage["text"] + arrow + "\n" + util.unitValueToText(sweep_voltage))
            else:
                self.previewWidget.setText(util.unitValueToText(voltage) + arrow + "\n" + util.unitValueToText(sweep_voltage))
        else:
            self.previewWidget.setText(util.unitValueToText(voltage))

    def updateUnitCyclerCalibrationUnit(self, unitText):
        units = [{"text": "mV", "factor": 1e-3}, {"text": "V", "factor": 1}]
        if unitText is not None:
            units.append({"text": unitText, "factor": 1})
        self.configWidgets["voltage"].cycler.setUnits(units)
        self.configWidgets["sweep_voltage"].cycler.setUnits(units)

    def valueChange(self, valueName, newValue):
        super(Widget, self).valueChange(valueName, newValue)
        if valueName in ["sweep_enable"]:
            self.segment.sequence.alignPorts()
        self.configDialog.updateFormulaPreview()

    def getTableViewInfo(self):
        return getTableViewInfo(self.getData())


def getTableViewInfo(data):
    voltage = data["voltage"]
    sweep_enable = data["sweep_enable"]
    tv = {
        "text": util.unitValueToText(voltage),
        "color": getTableColor(voltage),
    }
    if sweep_enable:
        sweep_voltage = data["sweep_voltage"]
        tv["text"] += " ↗" if Input.getValueFromState(voltage, replacer=Variables.replacer) < Input.getValueFromState(sweep_voltage, replacer=Variables.replacer) else " ↘"
        tv["next_text"] = util.unitValueToText(sweep_voltage)
        tv["next_color"] = getTableColor(sweep_voltage)
    else:
        tv["next_text"] = tv["text"]
        tv["next_color"] = tv["color"]
    return tv


def getTableColor(voltage):
    value = Input.getValueFromState(voltage, replacer=Variables.replacer)
    if value is None:
        return QtG.QColor(0, 0, 0)
    r = 0
    g = min(1, value / 10 if value > 0 else 0) ** 0.2
    b = min(1, -value / 10 if value < 0 else 0) ** 0.2
    return (r, g, b)


class ConfigDialog(PortState.ConfigDialog):
    def __init__(self, portStateWidget):
        self.formulaPreview = Formula.DatapointList()
        self.formulaPreview.setFixedSize(400, 300)
        super(ConfigDialog, self).__init__(portStateWidget)
        self.updateFormulaPreview()
        self.formulaPreview.plotWidget.setLabel("bottom", "time / ms")
        self.formulaPreview.plotWidget.setLabel("left", f"Value / m{portStateWidget.defaultUnit}")

    def generateConfigurationWidgets(self):
        return Design.VBox(
            Design.HBox(QtW.QLabel("Value"), Design.Spacer(), self.configWidgets["voltage"]),
            Design.HBox(
                self.configWidgets["sweep_enable"],
                Design.Spacer(),
                self.configWidgets["sweep_voltage"],
            ),
            Design.HBox(self.configWidgets["formula_enable"]),
            Design.HBox(
                self.configWidgets["formula_text"],
                self.configWidgets["formula_selection_button"],
            ),
            self.formulaPreview,
        )

    def updateVisibility(self):
        if self.isAboutToClose:
            return
        sweep_enable = self.configWidgets["sweep_enable"].get()
        formula_enable = self.configWidgets["formula_enable"].get()
        self.configWidgets["sweep_voltage"].setVisible(sweep_enable)
        self.configWidgets["formula_enable"].setVisible(sweep_enable)
        self.formulaPreview.setVisible(formula_enable and sweep_enable)
        self.configWidgets["formula_selection_button"].setVisible(formula_enable and sweep_enable)
        self.configWidgets["formula_text"].setVisible(formula_enable and sweep_enable)

    def updateFormulaPreview(self):
        try:
            stepCountFunction = hardware_util.getZotinoStepCount if crate.labsetup[self.portName]["module"] == "artiq.coredevice.zotino" else hardware_util.getFastinoStepCount
            duration = self.getSegmentDuration()
            voltage = Input.getValueFromState(
                self.portStateWidget.getValue("voltage"),
                reader=float,
                replacer=Variables.replacer,
            )
            sweep_voltage = Input.getValueFromState(
                self.portStateWidget.getValue("sweep_voltage"),
                reader=float,
                replacer=Variables.replacer,
            )
            formula_text = Input.getValueFromState(
                self.configWidgets["formula_text"].get(),
                reader=str,
                replacer=Variables.replacer,
            )
            dataX, dataY = hardware_util.formulaTextToDataPoints(stepCountFunction(duration), formula_text)
            dataX, dataY = hardware_util.scaleFormulaData(dataX, dataY, duration, voltage, sweep_voltage)
            dataX, dataY = hardware_util.interpolateFormulaDataToPrevious(dataX, dataY)
            self.formulaPreview.setData([x * 1e3 for x in dataX], [y * 1e3 for y in dataY])
        except Exception as e:
            print("Error in Formula Dialog:", e)
            traceback.print_exc()

    def getSegmentDuration(self):
        segment = crate.sequences[self.portStateWidget.segment.sequence.name]["segments"][self.portStateWidget.segment.name]
        return Input.getValueFromState(segment["duration"], reader=float, replacer=Variables.replacer)
