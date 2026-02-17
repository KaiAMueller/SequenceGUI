import copy
import time
import os

import numpy as np
import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW
import PySide6.QtGui as QtG

import threading

import gui.artiq_master_manager as artiq_master_manager
import gui.compiler
import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Dock as Dock
import gui.widgets.Input as Input
import gui.widgets.RPC as RPC
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.Viewer as Viewer

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
        global dock
        dock = self

        self.runButton = Design.RunButton()
        self.runButton.setToolTip("Compile and run selected multirun")
        self.runButton.setEnabled(False)
        self.runButton.clicked.connect(self.run)
        self.setRightWidget(self.runButton)

    def loadCrate(self):
        super(Dock, self).loadCrate(crate.multiruns)

    def changeSelection(self, newSelection):
        super().changeSelection(newSelection)
        self.runButton.setEnabled(newSelection is not None)

    def run(self):
        if self.configWidget is not None:
            self.configWidget.run()


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
            reader=float,
            changedCallback=lambda value: crate.MultiRun.VariableValueChange(self.multirun, self.dimension, self.name, "min", value),
            dontUpdateMetrics=True,
        )
        self.maxField = Input.TextField(
            default=crate.MultiRun.getVariableValue(self.multirun, self.dimension, self.name, "max"),
            reader=float,
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
