import numpy as np
import pyqtgraph as pyqtg
import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.settings as settings
import gui.widgets.Design as Design
import gui.widgets.Input as Input

NUMPY_FUNCTION_LIST = [
    "arcsin",
    "arccos",
    "arctan",
    "sin",
    "cos",
    "sqrt",
    "tan",
    "exp",
    "pi",
]


def translateFormulaToNumpy(formula):
    np_formula = formula.replace("^", "**")
    for i in range(len(NUMPY_FUNCTION_LIST)):
        func = NUMPY_FUNCTION_LIST[i]
        np_formula = np_formula.replace(func, f"$np_func_{i}")
    for i in range(len(NUMPY_FUNCTION_LIST)):
        j = len(NUMPY_FUNCTION_LIST) - i - 1
        func = NUMPY_FUNCTION_LIST[j]
        np_formula = np_formula.replace(f"$np_func_{j}", f"np.{func}")
    np_formula = np_formula.replace("np.np.", "np.")
    return np_formula


def evaluate(formula, x=0):
    try:
        return eval(translateFormulaToNumpy(formula), {"x": x, "np": np})
    except Exception:
        return None


def generatePixmap(formula="x", w=40, h=20, x0=0, x1=1, color=QtG.QColor(155, 0, 155, 255)):
    pixmap = QtG.QPixmap(w, h)
    pixmap.fill(QtG.QColor(20, 20, 20, 255) if settings.getDarkmode() else QtG.QColor(200, 200, 200, 255))
    try:
        assert formula is not None and x0 is not None and x1 is not None and x0 < x1
        data = [0] * w
        highest = float("-inf")
        lowest = float("inf")
        for x in range(w):
            data[x] = evaluate(formula, x / w * (x1 - x0) + x0)
            if data[x] is None:
                continue
            if data[x] > highest:
                highest = data[x]
            if data[x] < lowest:
                lowest = data[x]
        assert highest >= lowest
        painter = QtG.QPainter(pixmap)
        painter.setPen(QtG.QPen(color, 1, QtC.Qt.PenStyle.SolidLine))
        lastY = None
        for x in range(w):
            if lowest == highest:
                y = h // 2
            else:
                y = int(np.round((1 - (data[x] - lowest) / (highest - lowest)) * (h - 1)))
            if lastY is not None and (lastY - y > 1 or lastY - y < -1):
                painter.drawLine(x - 1, lastY, x, y)
            else:
                painter.drawPoint(x, y)
            lastY = y
        painter.end()
    except Exception:
        pass
    return pixmap


class DatapointList(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.plotWidget = pyqtg.PlotWidget(self)
        self.plot = self.plotWidget.plot(pen=(255, 255, 255) if settings.getDarkmode() else (0, 0, 0))
        self.plotWidget.setBackground((32, 33, 36) if settings.getDarkmode() else (255, 255, 255))
        self.plotWidget.setMenuEnabled(False)
        self.plotWidget.setMouseEnabled(x=False, y=False)
        self.plotWidget.enableAutoRange()
        self.layout().addWidget(self.plotWidget)

    def setData(self, dataX, dataY):
        self.plot.setData(dataX, dataY)


class Dialog(Design.DialogDesign):
    def __init__(self, formula, callback):
        super().__init__(title="Formula Dialog", leftCornerLabel="📈")
        self.formula = formula
        self.callback = callback

        self.doneButton = Design.Button(" done ")
        self.doneButton.clicked.connect(self.doneButtonPressed)

        self.cancelButton = Design.Button(" cancel ")
        self.cancelButton.clicked.connect(self.close)

        self.plotWidget = pyqtg.PlotWidget(self)
        self.plotWidget.setFixedSize(400, 300)
        self.plot = self.plotWidget.plot(pen=(255, 255, 255) if settings.getDarkmode() else (0, 0, 0))
        self.plotWidget.setMenuEnabled(False)
        self.plotWidget.disableAutoRange()
        self.plotWidget.sigRangeChanged.connect(lambda: self.evaluateFormula(self.formula))
        self.plotWidget.setBackground((32, 33, 36) if settings.getDarkmode() else (255, 255, 255))

        self.formulaField = Input.TextField(
            default=self.formula,
            reader=self.evaluateFormula,
            dontUpdateMetrics=True,
            alignment=QtC.Qt.AlignmentFlag.AlignLeft,
        )

        self.layout().addWidget(
            Design.VBox(
                Design.HBox(
                    QtW.QLabel("f(x) ="),
                    1,
                    self.formulaField,
                    self.doneButton,
                    self.cancelButton,
                ),
                Design.HintText("Left mouse drag to move, right mouse drag to zoom each axis"),
                self.plotWidget,
            )
        )

    def doneButtonPressed(self):
        self.callback(self.formula)
        self.close()

    def evaluateFormula(self, formula):
        try:
            np_formula = translateFormulaToNumpy(formula)

            x0 = self.plotWidget.viewRange()[0][0]
            x1 = self.plotWidget.viewRange()[0][1]
            data_x = np.linspace(x0, x1, self.width())
            data_y = []

            for x in data_x:
                exec(f"data_y.append({np_formula})")

            for y in data_y:
                if not isinstance(y, (int, float, complex)):
                    raise Exception

            self.plot.setData(data_x, data_y)
            self.formula = formula
            self.doneButton.setEnabled(True)
            return formula
        except Exception:
            self.doneButton.setEnabled(False)
            raise Exception


class SelectionButton(Design.Button):
    def __init__(self, text, callback):
        super().__init__(text)
        self.callback = callback
        self.clicked.connect(self.onClicked)

    def onClicked(self):
        dialog = SelectionDialog(self.callback)
        dialog.exec()


class SelectionDialog(Design.DialogDesign):
    def __init__(self, callback):
        super().__init__(title="Formula Selection Dialog", leftCornerLabel="🔍")
        self.setMinimumWidth(400)
        self.callback = callback
        formulas = {
            "Lin   | linear": "x",
            "Quad  | quadratic": "x^2",
            "Gauss | Gauss": "exp(-(x-0.5)^2*8^2)",
            "HW    | hann window": "0.5 - 0.5*cos(2*pi*x)",
            "BW    | blackman window": "0.42 - 0.5*cos(2*pi*x) + 0.08*cos(4*pi*x)",
            "HHW   | half hann window": "0.5 - 0.5*cos(pi*x)",
            "HBW   | half blackman window": "0.42 - 0.5*cos(pi*x) + 0.08*cos(2*pi*x)",
        }
        maxButtonTextLength = max([len(name) + len(formula) for name, formula in formulas.items()])
        formulasWidgetsDicts = [
            {
                "name": name,
                "formula": formula,
                "button": Design.Button(f"{name}     {' ' * (maxButtonTextLength - len(name) - len(formula))} {formula}"),
                "field": Input.FormulaField(
                    text="",
                    default=formula,
                    inputDisabled=True,
                ),
            }
            for name, formula in formulas.items()
        ]
        for formulaWidgets in formulasWidgetsDicts:
            formulaWidgets["button"].clicked.connect(lambda ignore, f={"name":formulaWidgets["name"], "formula":formulaWidgets["formula"]}: self.buttonClicked(f))
            formulaWidgets["button"].setFont(QtG.QFont("Consolas", 10))
            formulaWidgets["field"].textField.setVisible(False)
        self.layout().addWidget(
            Design.VBox(
                *[
                    Design.HBox(
                        Design.Spacer(),
                        formulaWidgets["button"],
                        formulaWidgets["field"],
                    )
                    for formulaWidgets in formulasWidgetsDicts
                ]
            )
        )

    def buttonClicked(self, formula):
        self.callback(formula)
        self.close()


def formulaDialog(formula):
    returnValue = []

    def callback(formula):
        returnValue.append(formula)

    dialog = Dialog(formula, callback)
    dialog.exec()
    return returnValue[0] if len(returnValue) > 0 else None
