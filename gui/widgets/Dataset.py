import copy

import numpy as np
import pyqtgraph as pyqtg
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW
import scipy as sp

import gui.settings as settings
import gui.widgets.Design as Design
import gui.widgets.Input as Input


def getInterpolationFunction(dataset):
    mode = dataset["interpolation_mode"]
    if len(dataset["x"]) < 2:
        return None
    elif len(dataset["x"]) < 3 and mode == "quadratic":
        mode = "linear"
    elif len(dataset["x"]) < 4 and mode == "cubic":
        mode = "quadratic"
    return sp.interpolate.interp1d(dataset["x"], dataset["y"], kind=mode)


def getInterpolationReader(dataset, factor=1):
    function = getInterpolationFunction(dataset)
    return lambda text: float(function(float(text))) * factor


class Dialog(Design.DialogDesign):
    def __init__(self, dataset, callback, dimensions=["x", "y"]):
        super().__init__(title="Dataset Dialog", leftCornerLabel="🗃️")
        self.dataset = (
            copy.deepcopy(dataset)
            if dataset is not None
            else {
                "x": [1, 2, 3],
                "y": [2, 3, 5],
            }
        )
        if "interpolation_mode" not in self.dataset:
            self.dataset["interpolation_mode"] = "quadratic"
        self.callback = callback
        self.dimensions = dimensions

        self.saveButton = Design.Button(" Save ")
        self.saveButton.clicked.connect(self.saveButtonPressed)

        self.cancelButton = Design.Button(" Cancel ")
        self.cancelButton.clicked.connect(self.close)

        self.plotStatusLabel = QtW.QLabel("")
        self.plotStatusLabel.setFont(QtG.QFont("Consolas", 10))
        self.plotStatusLabel.setObjectName("plotStatusLabel")

        self.tableWidget = QtW.QTableWidget()
        self.updateTable()

        self.addRowButton = Design.Button("➕")
        self.addRowButton.clicked.connect(self.addRow)

        self.removeRowButton = Design.Button("➖")
        self.removeRowButton.clicked.connect(self.removeRow)

        self.interpolationModeCombobox = QtW.QComboBox()
        self.interpolationModeCombobox.addItems(
            [
                "linear",
                "nearest",
                "zero",
                "slinear",
                "quadratic",
                "cubic",
                "previous",
                "next",
            ]
        )
        self.interpolationModeCombobox.setCurrentText(self.dataset["interpolation_mode"])
        self.interpolationModeCombobox.currentTextChanged.connect(lambda ignore: self.updatePlot())

        self.sortDataButton = Design.Button("Sort Data")
        self.sortDataButton.clicked.connect(self.sortDataButtonClicked)

        self.importDataButton = Design.Button("Import Data")
        self.importDataButton.clicked.connect(self.importDataButtonClicked)

        backgroundColor = (32, 33, 36) if settings.getDarkmode() else (255, 255, 255)

        self.plotWidget = pyqtg.PlotWidget(self)
        self.plotLine = self.plotWidget.plot(pen=(255, 255, 255) if settings.getDarkmode() else (0, 0, 0))
        self.plotPoints = self.plotWidget.plot(pen=None, symbol="+", symbolPen=backgroundColor, symbolBrush=(255, 0, 0))
        self.plotWidget.sigRangeChanged.connect(self.updatePlot)
        self.plotWidget.setMenuEnabled(False)
        self.plotWidget.setBackground(backgroundColor)
        self.updatePlot()

        self.resize(800, 600)
        self.layout().addWidget(
            Design.HBox(
                Design.VBox(
                    self.tableWidget,
                    Design.HBox(self.addRowButton, self.removeRowButton),
                ),
                1,
                Design.VBox(
                    self.plotWidget,
                    Design.HBox(self.sortDataButton, Design.Spacer(), self.plotStatusLabel),
                    Design.HBox(
                        self.importDataButton,
                        Design.Spacer(),
                        "Interpolation Mode:",
                        self.interpolationModeCombobox,
                        Design.Spacer(),
                        self.saveButton,
                        self.cancelButton,
                    ),
                ),
            )
        )

    def updateTable(self):
        try:
            self.tableWidget.itemChanged.disconnect(self.tableItemChanged)
        except Exception:
            pass
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setRowCount(len(self.dataset["x"]))
        self.tableWidget.setHorizontalHeaderLabels(self.dimensions)
        self.tableWidget.setColumnWidth(0, 48)
        self.tableWidget.setColumnWidth(1, 48)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setFixedWidth(120)
        self.tableWidget.horizontalScrollBar().setVisible(False)
        for i in range(len(self.dataset["x"])):
            self.tableWidget.setRowHeight(i, 15)
            self.tableWidget.setItem(i, 0, QtW.QTableWidgetItem(str(self.dataset["x"][i])))
            self.tableWidget.setItem(i, 1, QtW.QTableWidgetItem(str(self.dataset["y"][i])))
        self.tableWidget.itemChanged.connect(self.tableItemChanged)

    def tableItemChanged(self, item):
        try:
            self.dataset["x" if item.column() == 0 else "y"][item.row()] = float(item.text())
        except Exception:
            pass
        self.updatePlot()

    def addRow(self):
        self.dataset["x"].append(0)
        self.dataset["y"].append(0)
        self.tableWidget.setRowCount(len(self.dataset["x"]))
        self.tableWidget.setRowHeight(len(self.dataset["x"]) - 1, 15)
        self.tableWidget.setItem(len(self.dataset["x"]) - 1, 0, QtW.QTableWidgetItem(str(0)))
        self.tableWidget.setItem(len(self.dataset["x"]) - 1, 1, QtW.QTableWidgetItem(str(0)))
        self.updatePlot()

    def removeRow(self):
        if len(self.dataset["x"]) > 2:
            self.dataset["x"].pop()
            self.dataset["y"].pop()
            self.tableWidget.setRowCount(len(self.dataset["x"]))
            self.updatePlot()

    def updatePlot(self):
        self.plotPoints.setData(self.dataset["x"], self.dataset["y"])

        self.dataset["interpolation_mode"] = self.interpolationModeCombobox.currentText()
        try:
            function = getInterpolationFunction(self.dataset)
        except Exception as e:
            self.plotLine.setData([], [])
            self.saveButton.setEnabled(False)
            self.plotStatusLabel.setText(f"ERROR: {e}")
            return
        range = self.plotWidget.visibleRange()
        x = np.linspace(
            max(min(self.dataset["x"]), range.left()),
            min(max(self.dataset["x"]), range.right()),
            self.plotWidget.width(),
        )
        y = function(x)
        self.plotLine.setData(x, y)
        self.saveButton.setEnabled(True)
        self.plotStatusLabel.setText("")

    def saveButtonPressed(self):
        try:
            getInterpolationFunction(self.dataset)
        except Exception as e:
            Design.errorDialog("Error", f"Error when generating interpolation function:\n{e}")
            return
        self.callback(self.dataset)
        self.close()

    def importDataButtonClicked(self):
        path = QtW.QFileDialog.getOpenFileName(self, "Import Data", "", "CSV (*.csv);;All Files (*)")[0]
        if path == "" or path is None:
            return
        ImportDataDialog(self.dataset, path, self.dimensions).exec()
        self.updatePlot()
        self.updateTable()

    def sortDataButtonClicked(self):
        x_tuple, y_tuple = zip(*sorted(zip(self.dataset["x"], self.dataset["y"])))
        self.dataset["x"] = list(x_tuple)
        self.dataset["y"] = list(y_tuple)
        self.updatePlot()
        self.updateTable()


def datasetDialog(dataset, dimensions=["x", "y"]):
    returnValue = []

    def callback(dataset):
        returnValue.append(dataset)

    dialog = Dialog(dataset, callback, dimensions)
    dialog.exec()
    return returnValue[0] if len(returnValue) > 0 else None


class ImportDataDialog(Design.DialogDesign):
    def __init__(self, toBeWrittenDataset, path, dimensions):
        super().__init__(title="Dataset Import", leftCornerLabel="📥")
        self.toBeWrittenDataset = toBeWrittenDataset
        self.dimensions = dimensions
        try:
            self.textData = open(path).read()
        except Exception:
            Design.errorDialog("Error", "Could not open file.")
            self.close()

        self.saveButton = Design.Button(" done ")
        self.saveButton.clicked.connect(self.saveButtonPressed)

        self.cancelButton = Design.Button(" cancel ")
        self.cancelButton.clicked.connect(self.close)

        self.textDataPreviewField = QtW.QTextEdit()
        self.textDataPreviewField.setReadOnly(True)
        self.textDataPreviewField.setText(self.textData)
        self.textDataPreviewField.setFixedHeight(800)
        self.textDataPreviewField.setFixedWidth(800)
        self.textDataPreviewField.setLineWrapMode(QtW.QTextEdit.LineWrapMode.NoWrap)
        self.textDataPreviewField.verticalScrollBar().setValue(self.textDataPreviewField.verticalScrollBar().maximum())

        self.dataTable = QtW.QTableWidget()

        self.seperatorField = Input.TextField(default=",", changedCallback=self.updateTable)
        self.skipRowsField = Input.TextField(default="0", reader=int, changedCallback=self.updateTable)
        self.skipLastRowsField = Input.TextField(default="0", reader=int, changedCallback=self.updateTable)
        self.xColumnField = Input.TextField(default="0", reader=int, changedCallback=self.updateTable)
        self.yColumnField = Input.TextField(default="1", reader=int, changedCallback=self.updateTable)

        self.layout().addWidget(
            Design.HBox(
                self.textDataPreviewField,
                Design.VBox(
                    Design.Grid(
                        [
                            [QtW.QLabel("Seperator: "), self.seperatorField],
                            [QtW.QLabel("Ignore first rows: "), self.skipRowsField],
                            [QtW.QLabel("Ignore last rows: "), self.skipLastRowsField],
                            [
                                QtW.QLabel(f"Column for {dimensions[0]} values: "),
                                self.xColumnField,
                            ],
                            [
                                QtW.QLabel(f"Column for {dimensions[1]} values: "),
                                self.yColumnField,
                            ],
                        ]
                    ),
                    Design.Spacer(),
                    Design.HBox(self.saveButton, self.cancelButton),
                ),
                self.dataTable,
            )
        )
        self.updateTable()

    def readText(self):
        data = self.textData.split("\n")
        data = data[int(self.skipRowsField.get()) : len(data) - int(self.skipLastRowsField.get())]
        data = [row.split(self.seperatorField.get()) for row in data]
        data = [row for row in data if len(row) >= 2]
        x_column, y_column = int(self.xColumnField.get()), int(self.yColumnField.get())
        data = [[row[x_column], row[y_column]] for row in data]
        # sort by x values
        return data

    def updateTable(self, ignore=None):
        try:
            data = self.readText()
            self.dataTable.clear()
            self.dataTable.setRowCount(len(data))
            self.dataTable.setColumnCount(2)
            self.dataTable.setHorizontalHeaderLabels(self.dimensions)
            for i in range(len(data)):
                for j in range(2):
                    self.dataTable.setItem(i, j, QtW.QTableWidgetItem(str(data[i][j])))
        except Exception:
            self.dataTable.clear()

    def saveButtonPressed(self):
        try:
            data = self.readText()
            self.toBeWrittenDataset["x"] = [float(row[0]) for row in data]
            self.toBeWrittenDataset["y"] = [float(row[1]) for row in data]
            self.close()
        except Exception:
            Design.errorDialog("Error", "Could not parse data.")
