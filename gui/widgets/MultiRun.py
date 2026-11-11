import copy
import time
import os

import numpy as np
import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW
import PySide6.QtGui as QtG

import threading
from pathlib import Path

import gui.artiq_master_manager as artiq_master_manager
import gui.compiler
import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Dock as Dock
import gui.widgets.Input as Input
import gui.widgets.RPC as RPC
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.Viewer as Viewer
from gui.scan_plan import build_scan_plan

currentlyRunningVariables = None

dock = None
title = "🔁 Multi Run"


class Dock(Dock.ListConfigDockExtension):
    def __init__(self, gui):
        super(Dock, self).__init__(
            title=title,
            gui=gui,
            itemKind="MultiRun",
            widgetClass=Widget,
            backendCallbacks=crate.MultiRun,
            icon="🔁",
        )

        self.coreScanCodeButton = Design.IconButton(
            "🗔",
            self.showCoreScanCode
        )

        self.coreScanCodeButton.setToolTip(
            "Generate and display Core Scan ARTIQ code"
        )

        self.coreScanCodeButton.setEnabled(False)

        global dock
        dock = self

        self.runButton = Design.RunButton()
        self.runButton.setToolTip("Compile and run selected multirun")
        self.runButton.setEnabled(False)
        self.runButton.clicked.connect(self.run)

        # New Core Scan preview button
        self.coreScanPreviewButton = Design.Button(
            "Core Scan: Preview",
            size="medium"
        )
        self.coreScanPreviewButton.setToolTip(
            "Preview all scan values for single-job execution"
        )
        self.coreScanPreviewButton.setEnabled(False)
        self.coreScanPreviewButton.clicked.connect(self.previewCoreScan)

        self.coreScanRunButton = Design.RunButton()

        self.coreScanRunButton.setToolTip(
            "Execute the entire scan in one ARTIQ experiment"
        )

        self.coreScanRunButton.setEnabled(False)

        self.coreScanRunButton.clicked.connect(
            self.runCoreScan
        )




        self.setRightWidget(
            Design.HBox(
                self.coreScanPreviewButton,
                self.coreScanCodeButton,
                self.coreScanRunButton,
                self.runButton
            )
        )

    def loadCrate(self):
        super(Dock, self).loadCrate(crate.multiruns)

    def changeSelection(self, newSelection):
        super().changeSelection(newSelection)
        self.runButton.setEnabled(newSelection is not None)
        self.coreScanPreviewButton.setEnabled(newSelection is not None)
        self.coreScanRunButton.setEnabled(newSelection is not None)
        self.coreScanCodeButton.setEnabled(newSelection is not None)

    def run(self):
        if self.configWidget is not None:
            self.configWidget.run()

    def runCoreScan(self):
        if self.configWidget is not None:
            self.configWidget.runCoreScan()


    def previewCoreScan(self):
        import traceback

        print("[Core Scan] Button clicked", flush=True)

        try:
            if self.configWidget is None:
                print("[Core Scan] No MultiRun widget selected")
                return

            print("[Core Scan] Starting preview", flush=True)
            self.configWidget.previewCoreScan()
            print("[Core Scan] Preview finished", flush=True)

        except Exception:
            print(traceback.format_exc(), flush=True)

    def showCoreScanCode(self):
        if self.configWidget is not None:
            self.configWidget.previewCoreScan(
                show_code=True
            )



class Widget(Design.VBox):
    def __init__(self, name, dock):
        self.name = name
        self.dock = dock
        self.dimensionWidgets = {dimension: Dimension(dimension, self.name) for dimension in crate.MultiRun.getValue(self.name, "dimensions").keys()}
        self.dimensionWidgetsLayout = Design.VBox(*list(self.dimensionWidgets.values()))
        self.modeComboBox = Input.ComboBox(
            itemsGenerateFunction=lambda: [
                "scan",
                "monte carlo",
                "differential evolution",
            ],
            default=crate.MultiRun.getValue(self.name, "mode"),
            changedCallback=lambda mode: crate.MultiRun.ValueChange(self.name, "mode", mode),
        )
        
        
        self.addDimensionButton = Design.AlignedButton("Add Dimension")
        self.addDimensionButton.setFlat(True)
        self.addDimensionButton.clicked.connect(lambda: crate.MultiRun.DimensionAdd(self.name))
        super(Widget, self).__init__(
            Design.HBox(
                QtW.QLabel("mode"),
                self.modeComboBox,
                Design.Spacer(),
                Viewer.InfoButton(crate.multiruns[self.name]),
            ),
            self.dimensionWidgetsLayout,
            self.addDimensionButton,
            Design.Spacer(),
        )

    def valueChange(self, valueName, value):
        if valueName == "mode":
            self.modeComboBox.setCurrentText(value)
            stepsEnabled = value == "scan"
            for dimensionWidget in self.dimensionWidgets.values():
                dimensionWidget.stepsField.setVisible(stepsEnabled)
                dimensionWidget.stepsLabel.setVisible(stepsEnabled)


    def addDimensionWidget(self, dimension):
        self.dimensionWidgets[dimension] = Dimension(dimension, self.name)
        pos = sorted(list(self.dimensionWidgets.keys())).index(dimension)
        self.dimensionWidgetsLayout.layout().insertWidget(pos, self.dimensionWidgets[dimension])

    def deleteDimensionWidget(self, dimension):
        self.dimensionWidgetsLayout.layout().removeWidget(self.dimensionWidgets[dimension])
        self.dimensionWidgets[dimension].deleteLater()
        self.dimensionWidgets.pop(dimension)

    def run(self):
        if artiq_master_manager.test_mode:
            Design.errorDialog("Error", "Test device_db is active. Cannot run on Hardware.")
            return
        if crate.MultiRun.getValue(self.name, "mode") == "scan":
            self.scanRun()
        else:
            Design.errorDialog("Error", "Not implemented.")

    

    def previewCoreScan(self, show_code=False):

        if crate.MultiRun.getValue(self.name, "mode") != "scan":
            Design.errorDialog(
                "Core Scan",
                "Only scan mode is supported."
            )
            return

        dimensions = crate.MultiRun.getValue(
            self.name, "dimensions"
        )

        try:
            scan_plan = build_scan_plan(dimensions)
        except (ValueError, TypeError, KeyError) as e:
            Design.errorDialog("Core Scan Error", str(e))
            return

        # Limit this initial preview to small scans.
        if len(scan_plan) > 100:
            Design.errorDialog(
                "Core Scan",
                "The initial preview supports at most 100 scan points."
            )
            return

        # Select the sequence to scan.
        sequence = Design.comboBoxDialog(
            "Core Scan",
            "Select a sequence to scan",
            list(crate.sequences.keys()),
            defaultOption=SequenceEditor.dock.list.currentSelection,
        )

        if not sequence:
            return

        try:
            compiled_points = gui.compiler.compileScanPoints(
                sequence, scan_plan
            )
        except Exception as e:
            Design.errorDialog("Core Scan Error", str(e))
            return

        lines = []

        for point in compiled_points[:10]:

            parameters = ", ".join(
                f"{name} = {value}"
                for name, value in point["parameters"].items()
            )

            lines.append(
                f"Point {point['index'] + 1}: "
                f"{parameters}, "
                f"duration = {point['duration']:.3f} s"
            )

        total_duration = sum(
            point["duration"]
            for point in compiled_points
        )


        # Generate the complete single-job experiment.
        try:
            import ast

            code, codeID, combined_duration = (
                gui.compiler.compileCoreScanCode(
                    sequence,
                    scan_plan
                )
            )

            # Verify that the generated Python is syntactically valid.
            ast.parse(code)

        except Exception as e:
            import traceback
            traceback.print_exc()
            Design.errorDialog(
                "Core Scan Generation Error",
                str(e)
            )
            return


        message = (
            f"Sequence: {sequence}\n"
            f"Scan points: {len(compiled_points)}\n"
            f"Total duration: {total_duration:.3f} s\n\n"
            + "\n".join(lines)
        )

        if show_code:
            Viewer.Dialog(code).exec()
        else:
            Design.infoDialog("Core Scan Preview", message)


    
    def scanRun(self):
        sequence = Design.comboBoxDialog(
            "Sequence",
            "Select a sequence to multirun",
            list(crate.sequences.keys()),
            defaultOption=SequenceEditor.dock.list.currentSelection,
        )
        if sequence is None or sequence == "":
            return
        if not self.checkScanValidity():
            return
        if not Design.confirmationDialog(
            "Scan",
            f'MultiRun sequence "{sequence}"? This will include {self.getRunCount()} runs.',
        ):
            return
        pre_compile_rpc = crate.Sequences.getSequenceValue(sequence, "pre_compile_rpc")
        wait_for_pre_compile_rpc_finish = False
        if pre_compile_rpc is not None:
            if crate.RPC.getValue(pre_compile_rpc, "mode") != "normal":
                wait_for_pre_compile_rpc_finish = Design.confirmationDialog(
                    "Pre-Compile RPC",
                    f'Pre-Compile RPC "{pre_compile_rpc}" is not in normal mode, means they will all run in parallel. Wait for each RPC completion before compiling next?',
                )
        linespaces = []
        steps = []
        for dimData in crate.MultiRun.getValue(self.name, "dimensions").values():
            steps_ = int(dimData["steps"])
            linespaces.append(
                {
                    variableName: (
                        np.linspace(
                            float(variableData["min"]),
                            float(variableData["max"]),
                            steps_,
                        )
                        if variableData["mode"] == "linear"
                        else variableData["datalist"]
                    )
                    for variableName, variableData in dimData["variables"].items()
                }
            )
            steps.append(steps_)
        global currentlyRunningVariables
        currentlyRunningVariables = copy.deepcopy(crate.variables)
        progressDialog = Design.ProgressDialog("Scan", "Queueing runs...")
        cancelQueueing = False

        def setCancelQueueing():
            nonlocal cancelQueueing
            cancelQueueing = True

        progressDialog.onClose = setCancelQueueing
        progressDialog.show()
        runCount = self.getRunCount()
        i = 0
        while i < runCount:
            if cancelQueueing:
                Design.infoDialog(
                    "Linear Scan",
                    f"Queueing cancelled. {i} out of {runCount} runs queued.",
                )
                break
            for j, dimData in enumerate(list(crate.MultiRun.getValue(self.name, "dimensions").values())):
                divisor = 1
                for k in range(
                    j + 1,
                    len(list(crate.MultiRun.getValue(self.name, "dimensions").values())),
                ):
                    divisor *= steps[k]
                for variableName in dimData["variables"].keys():
                    value = linespaces[j][variableName][(i // divisor) % steps[j]]
                    currentlyRunningVariables[variableName]["value"] = str(value)
            if wait_for_pre_compile_rpc_finish and RPC.isRPCActive(pre_compile_rpc):
                time.sleep(0.1)
            else:
                gui.compiler.compileAndRun(sequence)
                progressDialog.setProgress((i + 1) / runCount)
                i += 1
            QtC.QCoreApplication.processEvents()
        progressDialog.close()
        currentlyRunningVariables = None


    def runCoreScan(self):

        # Do not execute when the test device_db is active.
        if artiq_master_manager.test_mode:
            Design.errorDialog(
                "Core Scan",
                "Test device_db is active. "
                "Cannot run on hardware."
            )
            return

        if crate.MultiRun.getValue(self.name, "mode") != "scan":
            Design.errorDialog(
                "Core Scan",
                "Only scan mode is supported."
            )
            return

        dimensions = crate.MultiRun.getValue(
            self.name, "dimensions"
        )

        # First implementation: one dimension only.
        if len(dimensions) != 1:
            Design.errorDialog(
                "Core Scan",
                "Core Scan currently supports "
                "exactly one dimension."
            )
            return

        if not self.checkScanValidity():
            return

        try:
            scan_plan = build_scan_plan(dimensions)

        except (ValueError, TypeError, KeyError) as e:
            Design.errorDialog("Core Scan Error", str(e))
            return

        if not 1 <= len(scan_plan) <= 100:
            Design.errorDialog(
                "Core Scan",
                "Use between 1 and 100 scan points "
                "for this initial implementation."
            )
            return

        # Select the experiment to scan.
        sequence = Design.comboBoxDialog(
            "Core Scan",
            "Select a sequence to scan",
            [
                name
                for name, data in crate.sequences.items()
                if not data.get("isDir", False)
            ],
            defaultOption=SequenceEditor.dock.list.currentSelection,
        )

        if not sequence:
            return

        if not Design.confirmationDialog(
            "Core Scan",
            f"Execute '{sequence}' with "
            f"{len(scan_plan)} scan points "
            f"in ONE ARTIQ experiment?"
        ):
            return

        try:
            codeID = gui.compiler.submitCoreScan(
                sequence,
                scan_plan
            )

        except Exception as e:
            import traceback
            traceback.print_exc()

            Design.errorDialog(
                "Core Scan Error",
                str(e)
            )
            return

        if codeID is not None:
            print(
                f"[Core Scan] Submitted {sequence} "
                f"with {len(scan_plan)} points "
                f"(codeID={codeID})",
                flush=True
            )






    def checkScanValidity(self):
        for dimName, dimData in crate.MultiRun.getValue(self.name, "dimensions").items():
            for variableName, variableData in dimData["variables"].items():
                if variableData["mode"] == "data list":
                    if int(dimData["steps"]) != len(variableData["datalist"]):
                        Design.errorDialog(
                            "Error",
                            f"Dimension \"{dimName}\" has {dimData['steps']} steps, but data list for variable \"{variableName}\" has {len(variableData['datalist'])} values.",
                        )
                        return False
        return True

    def getRunCount(self):
        runCount = 1
        for dimData in crate.MultiRun.getValue(self.name, "dimensions").values():
            runCount *= int(dimData["steps"])
        return runCount


class Dimension(Design.Frame):
    def __init__(self, dimension, multirun):
        self.dimension = dimension
        self.multirun = multirun
        self.variableWidgets = {name: Variable(name, self.dimension, self.multirun) for name in crate.MultiRun.getDimensionValue(self.multirun, self.dimension, "variables").keys()}
        self.variableWidgetsLayout = Design.VBox(*list(self.variableWidgets.values()))

        self.addVariableButton = Design.AlignedButton("Add Variable")
        self.addVariableButton.setFlat(True)
        self.addVariableButton.clicked.connect(self.addVariableButtonClicked)

        self.stepsField = Input.TextField(
            default=crate.MultiRun.getDimensionValue(self.multirun, self.dimension, "steps"),
            reader=int,
            changedCallback=lambda value: crate.MultiRun.DimensionValueChange(self.multirun, self.dimension, "steps", value),
            dontUpdateMetrics=True,
        )
        self.stepsLabel = QtW.QLabel("steps")
        stepsVisible = crate.MultiRun.getValue(self.multirun, "mode") == "scan"
        if not stepsVisible:
            self.stepsField.setVisible(False)
            self.stepsLabel.setVisible(False)
        self.stepsField.setFixedWidth(40)
        self.valueFields = {
            "steps": self.stepsField,
        }
        
        self.menu = QtW.QMenu()
        self.menu.addAction(
            "Delete Dimension",
            lambda: crate.MultiRun.DimensionDelete(self.multirun, self.dimension),
        )

        super(Dimension, self).__init__(
            Design.VBox(
                Design.HBox(
                    Design.HintText(f"{self.dimension}"),
                    Design.Spacer(),
                    self.stepsLabel,
                    self.stepsField,
                ),
                self.variableWidgetsLayout,
                Design.HBox(Design.Spacer(), self.addVariableButton),
            )
        )

    def contextMenuEvent(self, event):
        self.menu.exec(event.globalPos())

    def valueChange(self, valueName, value):
        self.valueFields[valueName].set(value)

    def addVariableButtonClicked(self):
        usedVariables = []
        for dimData in crate.MultiRun.getValue(self.multirun, "dimensions").values():
            usedVariables += list(dimData["variables"].keys())
        menu = Design.MenuSelectFromDirList(crate.variables, self.addVariableActionClicked, removedOptions=usedVariables)
        menu.exec(self.addVariableButton.mapToGlobal(QtC.QPoint(0, self.addVariableButton.height())))

    def addVariableActionClicked(self, variableName):
        if variableName is None or variableName == "":
            return
        if variableName in crate.MultiRun.getDimensionValue(self.multirun, self.dimension, "variables"):
            Design.errorDialog("Error", f'Variable "{variableName}" already exists.')
            return
        crate.MultiRun.VariableAdd(self.multirun, self.dimension, variableName)

    def addVariableWidget(self, variableName):
        if variableName is None or variableName == "" or variableName in self.variableWidgets:
            return
        self.variableWidgets[variableName] = Variable(variableName, self.dimension, self.multirun)
        self.variableWidgetsLayout.layout().addWidget(self.variableWidgets[variableName])

    def deleteVariableWidget(self, variableName):
        if variableName not in self.variableWidgets:
            return
        self.variableWidgetsLayout.layout().removeWidget(self.variableWidgets[variableName])
        self.variableWidgets[variableName].deleteLater()
        self.variableWidgets.pop(variableName)


class Variable(Design.HBox):
    def __init__(self, name, dimension, multirun):
        self.name = name
        self.dimension = dimension
        self.multirun = multirun
        self.modeField = Input.ComboBox(
            itemsGenerateFunction=lambda: ["linear", "data list"],
            default=crate.MultiRun.getVariableValue(self.multirun, self.dimension, self.name, "mode"),
            changedCallback=lambda mode: crate.MultiRun.VariableValueChange(self.multirun, self.dimension, self.name, "mode", mode),
        )
        self.minField = Input.TextField(
            default=crate.MultiRun.getVariableValue(self.multirun, self.dimension, self.name, "min"),
            reader=eval,
            changedCallback=lambda value: crate.MultiRun.VariableValueChange(self.multirun, self.dimension, self.name, "min", value),
            dontUpdateMetrics=True,
        )
        self.maxField = Input.TextField(
            default=crate.MultiRun.getVariableValue(self.multirun, self.dimension, self.name, "max"),
            reader=eval,
            changedCallback=lambda value: crate.MultiRun.VariableValueChange(self.multirun, self.dimension, self.name, "max", value),
            dontUpdateMetrics=True,
        )
        datalist = crate.MultiRun.getVariableValue(self.multirun, self.dimension, self.name, "datalist")
        self.datalistField = Input.DatalistEditor(
            textGenerator=lambda d: (f"{d[0]} ... {d[-1]} ({len(d)} Points)" if len(d) != 0 else "empty"),
            default=datalist,
            changedCallback=lambda value: crate.MultiRun.VariableValueChange(self.multirun, self.dimension, self.name, "datalist", value),
        )
        self.valueFields = {
            "datalist": self.datalistField,
            "mode": self.modeField,
            "min": self.minField,
            "max": self.maxField,
        }
        self.minField.setFixedWidth(60)
        self.maxField.setFixedWidth(60)
        self.removeButton = Design.DeleteButton()
        self.removeButton.clicked.connect(lambda: crate.MultiRun.VariableDelete(self.multirun, self.dimension, self.name))
        self.linearSettings = Design.HBox(
            "from",
            self.minField,
            QtW.QLabel("to"),
            self.maxField,
        )
        self.datasetSettings = Design.HBox(
            self.datalistField,
        )
        super(Variable, self).__init__(
            Design.Spacer(),
            self.name,
            self.modeField,
            self.linearSettings,
            self.datasetSettings,
            self.removeButton,
        )
        self.updateVisibility()

    def updateVisibility(self):
        mode = crate.MultiRun.getVariableValue(self.multirun, self.dimension, self.name, "mode")
        self.linearSettings.setVisible(mode == "linear")
        self.datasetSettings.setVisible(mode == "data list")

    def valueChange(self, valueName, value):
        self.valueFields[valueName].set(value)
        if valueName == "mode":
            self.updateVisibility()
