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
            changedCallback=lambda value: self.DACModifiedCallback("voltage",value),
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
            changedCallback=lambda value: self.DACModifiedCallback("sweep_voltage",value),
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
        # Load data (e.g. Optimal control) enable checkbox
        self.configWidgets["loadData_enable"] = Input.CheckBox(
            text="Use Dataset",
            default=self.getValue("loadData_enable"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "loadData_enable",
                value,
            ),
        )
        self.configWidgets["loaded_dataset"] = Input.DatasetEditor(
            text="See Dataset",
            dimensions=lambda: [
                self.getValue("dataset_unit_time")["text"],
                self.getValue("dataset_unit_voltage")["text"]
            ],
            default=self.getValue("loaded_dataset"),
            changedCallback=lambda value: crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName, 
                "loaded_dataset", 
                value,
            ),
        )



        # formula selection dialog button
        self.configWidgets["formula_selection_button"] = Formula.SelectionButton(
            text="📚",
            callback=lambda value: self.formulaModifiedCallback(value),
        )

        # sweep formula field
        self.configWidgets["formula_text"] = Input.FormulaField(
            text="Set Formula f(x) = ",
            default=self.getValue("formula_text"),
            replacer=Variables.replacer,
            changedCallback=lambda value: self.formulaModifiedCallback({"name": "Custom", "formula": value}),
        )
        self.getValue("formula_scale_factor") #initialize data["formula_scale_factor"]
        self.updatePreviewWidget()
        
        
    def DACModifiedCallback(self, valueName, value):
        crate.Sequences.PortStateValueChange(
            self.segment.sequence.name,
            self.segment.name,
            self.portName,
            valueName,
            value,
        )
        
        if self.getValue("formula_enable"):
            formula = self.getValue("formula_text")
            formula_scale_factor = self.getScaleFactor(Variables.replacer(formula))
            crate.Sequences.PortStateValueChange(
                self.segment.sequence.name,
                self.segment.name,
                self.portName,
                "formula_scale_factor",
                formula_scale_factor,
            )
    
    def formulaModifiedCallback(self, value):
        crate.Sequences.PortStateValueChange(
            self.segment.sequence.name,
            self.segment.name,
            self.portName,
            "formula_text",
            value["formula"],
        )
        
        crate.Sequences.PortStateValueChange(
            self.segment.sequence.name,
            self.segment.name,
            self.portName,
            "formula_name",
            value["name"],
        )
        
        formula_scale_factor = self.getScaleFactor(Variables.replacer(value["formula"]))
        crate.Sequences.PortStateValueChange(
            self.segment.sequence.name,
            self.segment.name,
            self.portName,
            "formula_scale_factor",
            formula_scale_factor,
        )
        
    def getScaleFactor(self, value):
        #Get the scale factor of the formular
        voltage = self.getValue("voltage")
        sweep_voltage = self.getValue("sweep_voltage")
        durartion = 1
        dataLenght = 1024
        dataX, dataY = hardware_util.formulaTextToDataPoints(dataLenght, value)
        voltage_value = util.unitValueToValue(voltage, Variables.replacer)
        sweep_voltage_value = util.unitValueToValue(sweep_voltage, Variables.replacer)
        return hardware_util.formulaScaleFactor(dataX, dataY, durartion, voltage_value, sweep_voltage_value)
        
    def getFormulaSelection(self):
        return ["Gauss", "Custom"]

    def updatePreviewWidget(self):
        voltage = self.getValue("voltage")
        sweep_enable = self.getValue("sweep_enable")
        formula_enable = self.getValue("formula_enable")
        loadData_enable = self.getValue("loadData_enable")

        if sweep_enable:
            sweep_voltage = self.getValue("sweep_voltage")
            arrow = " ↗ " if Input.getValueFromState(voltage, replacer=Variables.replacer) < Input.getValueFromState(sweep_voltage, replacer=Variables.replacer) else " ↘ "
            if formula_enable:
                formula_name = self.getValue("formula_name")
                if voltage["unit"] == sweep_voltage["unit"]:
                    self.previewWidget.setText(voltage["text"] + arrow + util.unitValueToText(sweep_voltage) + "\n" + formula_name.split()[0])
                else:
                    self.previewWidget.setText(util.unitValueToText(voltage) + arrow + "\n" + util.unitValueToText(sweep_voltage) + "\n" +  formula_name.split()[0])
            else:
                if voltage["unit"] == sweep_voltage["unit"]:
                    self.previewWidget.setText(voltage["text"] + arrow + "\n" + util.unitValueToText(sweep_voltage))
                else:
                    self.previewWidget.setText(util.unitValueToText(voltage) + arrow + "\n" + util.unitValueToText(sweep_voltage))
        elif loadData_enable:
            dataset = self.getValue("loaded_dataset")
            self.previewWidget.setText("Dataset"+ "\n" + dataset["importDataFileName"])
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
    formula_enable = data["formula_enable"]
    tv = {
        "text": util.unitValueToText(voltage),
        "color": getTableColor(voltage),
    }
    if sweep_enable:
        sweep_voltage = data["sweep_voltage"]
        tv["text"] += " ↗" if Input.getValueFromState(voltage, replacer=Variables.replacer) < Input.getValueFromState(sweep_voltage, replacer=Variables.replacer) else " ↘"
        tv["text"] += "\n" + util.unitValueToText(sweep_voltage)
        if formula_enable:
            formula_name = data["formula_name"]
            tv["text"] += "\n" + formula_name.split()[0]
            next_voltage = getFormulaLastVoltage(data)
            tv["next_text"] = util.unitValueToText(next_voltage)
            tv["next_color"] = getTableColor(next_voltage)
        else:
            tv["next_text"] = util.unitValueToText(sweep_voltage)
            tv["next_color"] = getTableColor(sweep_voltage)
    else:
        tv["next_text"] = tv["text"]
        tv["next_color"] = tv["color"]
    return tv

def getFormulaLastVoltage(data):
    formula_scale_factor = data["formula_scale_factor"]
    last_voltage = Formula.evaluate(Variables.replacer(data["formula_text"]), x=1) * formula_scale_factor["scaleY"] + formula_scale_factor["offsetY"]
    return util.textToUnitValue(last_voltage, data["sweep_voltage"]["unit"])

    
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
            Design.HBox(
                self.configWidgets["loadData_enable"],
                Design.Spacer(),
                self.configWidgets["loaded_dataset"],
            ),
        )

    def updateVisibility(self):
        if self.isAboutToClose:
            return
        loadData_enable = self.configWidgets["loadData_enable"].get()
        if loadData_enable:
            self.configWidgets["sweep_enable"].set(False)
            self.configWidgets["formula_enable"].set(False)
            self.configWidgets["sweep_enable"].changedCallback(False)
            self.configWidgets["formula_enable"].changedCallback(False)
        sweep_enable = self.configWidgets["sweep_enable"].get()
        formula_enable = self.configWidgets["formula_enable"].get()

        self.configWidgets["voltage"].setVisible(not loadData_enable)
        self.configWidgets["sweep_enable"].setVisible(not loadData_enable)
        self.configWidgets["sweep_voltage"].setVisible(sweep_enable and not loadData_enable)
        self.configWidgets["formula_enable"].setVisible(sweep_enable and not loadData_enable)
        self.formulaPreview.setVisible(formula_enable and sweep_enable)
        self.configWidgets["formula_selection_button"].setVisible(formula_enable and sweep_enable)
        self.configWidgets["formula_text"].setVisible(formula_enable and sweep_enable)
        self.configWidgets["loadData_enable"].setVisible(True)
        self.configWidgets["loaded_dataset"].setVisible(loadData_enable)

    def updateFormulaPreview(self):
        try:
            module_to_stepCountFunction = {
                "artiq.coredevice.zotino": hardware_util.getZotinoStepCount,
                "artiq.coredevice.fastino": hardware_util.getFastinoStepCount,
                "custom.CurrentDriver": hardware_util.getCurrentDriverStepCount,
            }
            stepCountFunction = module_to_stepCountFunction.get(crate.labsetup[self.portName]["module"], hardware_util.getZotinoStepCount)
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
