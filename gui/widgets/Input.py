import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.widgets.Datalist as Datalist
import gui.widgets.Dataset as Dataset
import gui.widgets.Design as Design
import gui.widgets.Formula as Formula
from gui.widgets.Log import log


class ShortcutEventFilter(QtC.QObject):
    def __init__(self):
        QtC.QObject.__init__(self)
        self.installEventFilter(self)

    def eventFilter(self, obj, e):
        if obj == self:
            if e.type() == QtC.QEvent.Type.KeyPress:
                if e.modifiers() == QtC.Qt.KeyboardModifier.ControlModifier:
                    self.parent().event(e)
                    return True
        return super().eventFilter(obj, e)


# class RedOutlineLineEdit(QtW.QLineEdit):
#     def __init__(self, default, redOutlineEnabled):
#         QtW.QLineEdit.__init__(self, default)
#         self.redOutlineEnabled = redOutlineEnabled

#     def setRedOutline(self, redOutlineEnabled):
#         self.redOutlineEnabled = redOutlineEnabled

#     def paintEvent(self, e: QtG.QPaintEvent):
#         QtW.QLineEdit.paintEvent(self, e)
#         if self.redOutlineEnabled:
#             painter = QtG.QPainter(self)
#             painter.setPen(QtC.Qt.PenStyle.NoPen)
#             painter.setBrush(QtG.QColor(255, 0, 0, 30))
#             painter.drawRect(0, 0, self.width(), self.height())


class RedOutlineWidget:
    def __init__(self, cls, redOutlineEnabled=False):
        self.cls = cls
        self.redOutlineEnabled = redOutlineEnabled

    def setRedOutline(self, redOutlineEnabled):
        self.redOutlineEnabled = redOutlineEnabled

    def paintEvent(self, e: QtG.QPaintEvent):
        result = self.cls.paintEvent(self, e)
        if self.redOutlineEnabled:
            painter = QtG.QPainter(self)
            painter.setPen(QtC.Qt.PenStyle.NoPen)
            painter.setBrush(QtG.QColor(255, 0, 0, 30))
            painter.drawRect(0, 0, self.width(), self.height())
            painter.end()
        return result


class TextField(RedOutlineWidget, QtW.QLineEdit):  # , ShortcutEventFilter):
    def __init__(
        self,
        default="0",
        reader=None,
        replacer=None,
        changedCallback=None,
        dontUpdateMetrics=False,
        alignment=QtC.Qt.AlignmentFlag.AlignRight,
    ):
        self.reader = reader if reader is not None else lambda x: x
        self.replacer = replacer if replacer is not None else lambda x: x
        self.changedCallback = changedCallback
        self.dontUpdateMetrics = dontUpdateMetrics
        # ShortcutEventFilter.__init__(self)
        QtW.QLineEdit.__init__(self, default)
        RedOutlineWidget.__init__(self, QtW.QLineEdit)
        self.setFont(Design.ValueFont())
        self.setObjectName("inputField")
        self.setAlignment(alignment)
        self.last_valid_value = None
        self.getValue()
        self.updateMetrics()
        self.textChanged.connect(self.onTextChanged)
        self.editingFinished.connect(self.onEditingFinished)
        self.widthHint = None

    def onTextChanged(self):
        self.updateMetrics()
        self.getValue()

    def onEditingFinished(self):
        if self.changedCallback is not None:
            if self.getValue() is not None:
                self.changedCallback(self.get())
        self.clearFocus()

    def updateMetrics(self):
        if self.dontUpdateMetrics:
            return
        self.widthHint = self.fontMetrics().boundingRect(self.text() + "000").width()
        self.setMaximumWidth(self.widthHint)

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        if self.widthHint is not None:
            size.setWidth(self.widthHint)
        return size

    def getValue(self):
        try:
            value = self.reader(self.replacer(self.text()))
        except Exception:
            value = None
        if value is None:
            self.setRedOutline(True)
        else:
            self.last_valid_value = value
            self.setRedOutline(False)
        return value

    def get(self):
        return self.text()

    def set(self, text):
        self.setText(text)
        self.updateMetrics()
        self.getValue()


class UnitCycler(RedOutlineWidget, Design.Button):
    def __init__(
        self,
        units,
        default=None,
        changedCallback=None,
        fixedWidth=30,
    ):
        Design.Button.__init__(self, units[0]["text"])
        RedOutlineWidget.__init__(self, Design.Button)
        self.setFont(Design.ValueFont())
        self.setObjectName("UnitCycler")
        self.setFlat(False)
        self.units = units
        self.unit = units[0]
        self.changedCallback = changedCallback
        self.setFixedWidth(fixedWidth)
        if default is not None and default != "":
            self.set(default)
        else:
            self.updateBorder()
        self.clicked.connect(self.cycleUnit)
        self.setFocusPolicy(QtC.Qt.FocusPolicy.NoFocus)

    def set(self, unit):
        if unit in self.units:
            for i in range(self.units.index(unit)):
                self.units.append(self.units.pop(0))
        self.setText(unit["text"])
        self.unit = unit
        self.updateBorder()

    def updateBorder(self):
        if self.unit in self.units:
            self.setRedOutline(False)
        else:
            self.setRedOutline(True)

    def get(self):
        return self.unit

    def setUnits(self, units):
        currentUnit = self.get()
        self.units = units
        if currentUnit in units:
            self.set(currentUnit)
        self.updateBorder()

    def cycleUnit(self):
        if len(self.units) == 1:
            return
        menu = QtW.QMenu()
        for unit in self.units:
            if unit == self.unit:
                continue
            action = menu.addAction(unit["text"])
            action.setFont(Design.ValueFont())
            action.triggered.connect(lambda checked, unit=unit: self.unitSelected(unit))
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def unitSelected(self, unit):
        self.set(unit)
        if self.changedCallback is not None:
            self.changedCallback(self.unit)


class LineEditWithShortcutEventFilterAndRedOutline(RedOutlineWidget, QtW.QLineEdit):  # , ShortcutEventFilter):
    def __init__(self, text):
        # ShortcutEventFilter.__init__(self)
        QtW.QLineEdit.__init__(self, text)
        RedOutlineWidget.__init__(self, QtW.QLineEdit)


class UnitValueField(RedOutlineWidget, Design.Frame):
    def __init__(
        self,
        default,
        allowedUnits,
        reader=float,
        replacer=None,
        changedCallback=None,
        dontUpdateMetrics=False,
        alignment=QtC.Qt.AlignmentFlag.AlignRight,
    ):
        self.reader = reader
        self.replacer = replacer if replacer is not None else lambda x: x
        self.changedCallback = changedCallback
        self.dontUpdateMetrics = dontUpdateMetrics
        self.readOnly = False
        self.lineEdit = LineEditWithShortcutEventFilterAndRedOutline(default["text"])
        self.lineEdit.setFont(Design.ValueFont())
        self.lineEdit.setObjectName("inputField")
        self.lineEdit.setAlignment(alignment)
        self.last_valid_value = None
        self.cycler = UnitCycler(allowedUnits, default["unit"], changedCallback=self.onCyclerChanged)
        self.cycler.setFlat(True)
        Design.Frame.__init__(self, Design.HBox(self.lineEdit, self.cycler))
        RedOutlineWidget.__init__(self, Design.Frame)
        self.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.setObjectName("UnitValueField")
        self.getValue()
        self.updateMetrics()
        self.lineEdit.textChanged.connect(self.onTextChanged)
        self.lineEdit.editingFinished.connect(self.onEditingFinished)
        self.lineEdit.minimumSizeHint = self.lineEditMinimumSizeHint
        self.widthHint = None

    def onTextChanged(self):
        self.updateMetrics()
        self.getValue()

    def onEditingFinished(self):
        if self.getValue() is not None:
            if self.changedCallback is not None:
                self.changedCallback(self.get())
        self.lineEdit.clearFocus()

    def updateMetrics(self):
        if self.dontUpdateMetrics:
            return
        self.widthHint = self.lineEdit.fontMetrics().boundingRect(self.lineEdit.text() + "000").width()
        self.lineEdit.setMaximumWidth(self.widthHint)

    def lineEditMinimumSizeHint(self):
        size = QtW.QLineEdit.minimumSizeHint(self.lineEdit)
        if self.widthHint is not None:
            size.setWidth(self.widthHint)
        return size

    def onCyclerChanged(self, s: str):
        if self.readOnly:
            if self.last_valid_value is not None:
                self.setValue(self.last_valid_value)
        else:
            if self.getValue() is not None:
                if self.changedCallback is not None:
                    self.changedCallback(self.get())

    def getValue(self):
        try:
            value = self.reader(self.replacer(self.lineEdit.text()))
        except Exception:
            value = None
        if value is not None and self.cycler is not None:
            value *= self.cycler.get()["factor"]
        if value is None:
            self.setRedOutline(True)
            self.lineEdit.setRedOutline(True)
        else:
            self.last_valid_value = value
            self.setRedOutline(False)
            self.lineEdit.setRedOutline(False)
        return value

    def setReadOnly(self, readOnly):
        self.readOnly = readOnly
        self.lineEdit.setReadOnly(readOnly)

    def get(self):
        return {
            "text": self.lineEdit.text(),
            "unit": self.cycler.get(),
        }

    def set(self, data):
        self.lineEdit.setText(data["text"])
        self.cycler.set(data["unit"])
        self.updateMetrics()
        self.getValue()

    def setValue(self, value):
        self.lineEdit.setText(str(round(value / self.cycler.get()["factor"], 6)))
        self.updateMetrics()
        self.getValue()

    def setText(self, text):
        self.lineEdit.setText(text)
        self.updateMetrics()
        self.getValue()

    def getText(self):
        return self.lineEdit.text() + " " + self.cycler.text()


def getValueFromState(state, reader=float, replacer=None):
    if state is None:
        return None
    try:
        if type(state) is dict:
            text = state["text"]
        else:
            text = state
        if replacer is not None:
            text = replacer(text)
        value = reader(text)
        if type(state) is dict and "unit" in state and state["unit"] is not None:
            value *= state["unit"]["factor"]
        return value
    except Exception as e:
        log(e)
        return None


class BigComboBox(Design.Button):
    def __init__(self, itemsGenerateFunction, default, changedCallback=None):
        super(BigComboBox, self).__init__(self.itemToText(default), flat=False, size="medium")
        self.setObjectName("BigComboBox")
        self.setFont(Design.SmallValueFont())
        self.set(default)
        self.currentSelection = default
        self.itemsGenerateFunction = itemsGenerateFunction
        self.changedCallback = changedCallback
        self.clicked.connect(self.onClicked)

    def onClicked(self):
        menu = QtW.QMenu()
        for item in self.itemsGenerateFunction():
            action = menu.addAction(item)
            action.setFont(Design.SmallValueFont())
            action.triggered.connect(lambda checked, item=item: self.itemSelected(item))
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def itemSelected(self, item):
        if item == self.currentSelection:
            return
        self.set(item)
        if self.changedCallback is not None:
            self.changedCallback(item)

    def itemToText(self, item):
        return item

    def updateItems(self, oldName, newName):
        if self.currentSelection == oldName:
            self.set(newName)

    def set(self, item):
        self.currentSelection = item
        self.setToolTip(item)
        self.setText(self.itemToText(item))

    def get(self):
        return self.currentSelection


class ComboBox(QtW.QComboBox):  # , ShortcutEventFilter):
    def __init__(
        self,
        itemsGenerateFunction,
        default=None,
        changedCallback=None,
        emptySelectionPossible=False,
    ):
        # ShortcutEventFilter.__init__(self)
        QtW.QComboBox.__init__(self)
        self.setFont(Design.ValueFont())
        self.itemsGenerateFunction = itemsGenerateFunction
        self.changedCallback = changedCallback
        self.emptySelectionPossible = emptySelectionPossible
        if self.emptySelectionPossible:
            self.addItem("")
        self.addItems(self.itemsGenerateFunction())
        if default is not None:
            self.setCurrentText(default)
        else:
            self.setCurrentIndex(0)
        self.connectCallback()

    def onChanged(self, text):
        self.changedCallback(text if text != "" else None)

    def connectCallback(self):
        if self.changedCallback is not None:
            self.currentTextChanged.connect(self.onChanged)

    def disconnectCallback(self):
        if self.changedCallback is not None:
            self.currentTextChanged.disconnect(self.onChanged)

    def mousePressEvent(self, e) -> None:
        self.updateItems()
        return super().mousePressEvent(e)

    def updateItems(self, oldName=None, newName=None):
        currentText = self.currentText()
        if currentText == oldName:
            currentText = newName
        self.disconnectCallback()
        self.clear()
        if self.emptySelectionPossible:
            self.addItem("")
        self.addItems(self.itemsGenerateFunction())
        self.setCurrentText(currentText)
        self.connectCallback()

    def set(self, text):
        if text is None:
            text = ""
        self.disconnectCallback()
        self.setCurrentText(text)
        self.connectCallback()

    def get(self):
        text = self.currentText()
        return text if text != "" else None


class CheckBox(QtW.QCheckBox):
    def __init__(self, default=False, changedCallback=None, text=None):
        if text is not None:
            super(CheckBox, self).__init__(text)
        else:
            super(CheckBox, self).__init__()
        self.changedCallback = changedCallback
        self.setFont(Design.ValueFont())
        self.setChecked(default)
        self.clicked.connect(self.onClicked)

    def onClicked(self):
        if self.changedCallback is not None:
            self.changedCallback(self.get())

    def set(self, value):
        self.setChecked(value)

    def get(self):
        return self.isChecked()


class ToggleButton(QtW.QPushButton):
    def __init__(self, default=False, changedCallback=None, states=["ON", "OFF"]):
        super(ToggleButton, self).__init__(states[0 if default else 1])
        self.setFont(Design.ValueFont())
        self.changedCallback = changedCallback
        self.states = states
        self.setCheckable(True)
        self.setChecked(default)
        self.clicked.connect(self.onClicked)
        self.setFocusPolicy(QtC.Qt.FocusPolicy.NoFocus)

    def onClicked(self):
        self.updateText()
        if self.changedCallback is not None:
            self.changedCallback(self.get())

    def set(self, value):
        self.setChecked(value)
        self.updateText()

    def updateText(self):
        self.setText(self.states[0 if self.isChecked() else 1])

    def get(self):
        return self.isChecked()


class FormulaField(Design.HBox):
    def __init__(
        self,
        default="x",
        inputDisabled=False,
        text="f(x) = ",
        replacer=None,
        changedCallback=None,
        orientation=QtC.Qt.Orientation.Horizontal,
        pixmapWidth=60,
        pixmapHeight=30,
        x0=0,
        x1=1,
    ):
        self.replacer = replacer if replacer is not None else lambda x: x
        self.changedCallback = changedCallback
        self.x0 = x0
        self.x1 = x1
        self.textField = TextField(
            default,
            reader=Formula.evaluate,
            replacer=replacer,
            changedCallback=changedCallback,
            dontUpdateMetrics=False,
            alignment=QtC.Qt.AlignmentFlag.AlignLeft,
        )
        if inputDisabled:
            self.textField.setReadOnly(True)
        self.textField.textChanged.connect(self.updatePixmap)
        self.pixmap = QtW.QLabel()
        self.pixmap.setFixedSize(pixmapWidth, pixmapHeight)
        self.updatePixmap()
        boxClass = Design.VBox if orientation == QtC.Qt.Orientation.Vertical else Design.HBox
        super(FormulaField, self).__init__(boxClass(Design.HBox(QtW.QLabel(text), self.textField), self.pixmap))

    def set(self, formula):
        self.textField.set(formula)
        self.updatePixmap()

    def get(self):
        return self.textField.get()

    def setPixmapBoundaries(self, x0, x1):
        self.x0 = x0
        self.x1 = x1
        self.updatePixmap()

    def updatePixmap(self):
        try:
            self.pixmap.setPixmap(
                Formula.generatePixmap(
                    formula=self.replacer(self.textField.get()),
                    w=self.pixmap.width() - 2,
                    h=self.pixmap.height() - 2,
                    x0=self.x0,
                    x1=self.x1,
                )
            )
        except Exception:
            pass


class FormulaEditor(QtW.QPushButton):
    def __init__(self, preText="f(x) = ", default="x", changedCallback=None):
        super(FormulaEditor, self).__init__(preText + default)
        self.preText = preText
        self.formula = default
        self.setFont(Design.ValueFont())
        self.changedCallback = changedCallback
        self.clicked.connect(self.onClicked)

    def onClicked(self):
        formula = Formula.formulaDialog(self.formula)
        if formula is None or formula == "" or self.formula == formula:
            return
        self.set(formula)
        if self.changedCallback is not None:
            self.changedCallback(formula)

    def get(self):
        return self.formula

    def set(self, formula):
        self.formula = formula
        self.setText(self.preText + formula)


class DatasetEditor(QtW.QPushButton):
    def __init__(
        self,
        text="Edit Dataset",
        dimensions=["x", "y"],
        default=None,
        changedCallback=None,
    ):
        super(DatasetEditor, self).__init__(text)
        self.dimensions = dimensions
        self.dataset = default
        self.setFont(Design.ValueFont())
        self.changedCallback = changedCallback
        self.clicked.connect(self.onClicked)

    def onClicked(self):
        dimensions = self.dimensions if type(self.dimensions) is list else self.dimensions()
        dataset = Dataset.datasetDialog(self.dataset, dimensions)
        if dataset is None or self.dataset == dataset:
            return
        self.set(dataset)
        if self.changedCallback is not None:
            self.changedCallback(dataset)

    def get(self):
        return self.dataset

    def set(self, dataset):
        self.dataset = dataset


class DatalistEditor(QtW.QPushButton):
    def __init__(self, textGenerator=lambda: "Edit Datalist", default=[], changedCallback=None):
        super(DatalistEditor, self).__init__(textGenerator(default))
        self.textGenerator = textGenerator
        self.datalist = default
        self.setFont(Design.ValueFont())
        self.changedCallback = changedCallback
        self.clicked.connect(self.onClicked)

    def onClicked(self):
        datalist = Datalist.datalistDialog(self.datalist)
        if datalist is None or self.datalist == datalist:
            return
        self.setText(self.textGenerator(datalist))
        self.set(datalist)
        if self.changedCallback is not None:
            self.changedCallback(datalist)

    def get(self):
        return self.datalist

    def set(self, datalist):
        self.datalist = datalist


class CodeEditor(QtW.QPlainTextEdit):
    def __init__(self, default="", changedCallback=None):
        super(CodeEditor, self).__init__()
        self.changedCallback = changedCallback
        self.setFont(Design.SmallValueFont())
        self.setTabStopDistance(QtG.QFontMetricsF(self.font()).horizontalAdvance(" ") * 4)
        self.setWordWrapMode(QtG.QTextOption.WrapMode.NoWrap)
        self.setPlainText(default)

    def keyPressEvent(self, e):
        if e.key() == QtC.Qt.Key.Key_Tab:
            self.insertPlainText(" " * 4)
        else:
            super().keyPressEvent(e)

    def onEditingFinished(self):
        self.set(self.toPlainText().replace("\t", "    "))
        if self.changedCallback is not None:
            self.changedCallback(self.get())

    def focusOutEvent(self, e):
        self.onEditingFinished()
        super().focusOutEvent(e)

    def get(self):
        return self.toPlainText()

    def set(self, text):
        cursor = self.textCursor()
        cursor.select(QtG.QTextCursor.SelectionType.Document)
        cursor.insertText(text)


class KeyValueEditor(QtW.QTableWidget):
    def __init__(
        self,
        default,
        changedCallback,
        keyReplacer=None,
        valueReplacer=None,
    ):
        super(KeyValueEditor, self).__init__()
        self.data = default
        self.changedCallback = changedCallback
        self.keyReplacer = keyReplacer if keyReplacer is not None else lambda x: x
        self.valueReplacer = valueReplacer if valueReplacer is not None else lambda x: x
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Key", "Value"])
        self.set(default)
        self.itemChanged.connect(self.onItemChanged)

    def set(self, data):
        self.data = data
        self.setRowCount(len(data) + 1)
        i = 0
        for key, value in data.items():
            self.setItem(i, 0, QtW.QTableWidgetItem(key))
            self.setItem(i, 1, QtW.QTableWidgetItem(value))
            i += 1

    def get(self):
        data = {}
        for i in range(self.rowCount() - 1):
            key = self.item(i, 0).text()
            value = self.item(i, 1).text()
            data[key] = value
        return data

    def getValue(self):
        data = {}
        for i in range(self.rowCount() - 1):
            keyItem = self.item(i, 0)
            valueItem = self.item(i, 1)
            key = keyItem.text() if keyItem is not None else ""
            value = valueItem.text() if valueItem is not None else ""
            data[key] = value
        return data

    def onItemChanged(self, item):
        if item.text() == "" and item.row() == self.rowCount() - 1:
            return
        if item.row() == self.rowCount() - 1 and item.column() == 0:
            self.setRowCount(self.rowCount() + 1)
            self.setItem(self.rowCount() - 1, 0, QtW.QTableWidgetItem(""))
            self.setItem(self.rowCount() - 1, 1, QtW.QTableWidgetItem(""))
        if self.changedCallback is not None:
            self.changedCallback(self.getValue())
