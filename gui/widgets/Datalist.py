import copy

import PySide6.QtWidgets as QtW

import gui.widgets.Design as Design


def datalistDialog(datalist: list):
    returnValue = []

    def callback(datalist):
        returnValue.append(datalist)

    dialog = Dialog(datalist, callback)
    dialog.exec()
    return returnValue[0] if len(returnValue) > 0 else None


class Dialog(Design.DialogDesign):
    def __init__(self, datalist, callback):
        super().__init__(title="Datalist Dialog", leftCornerLabel="🗃️")
        self.datalist = copy.deepcopy(datalist) if datalist is not None else [0, 1, 2, 3]
        self.callback = callback

        self.saveButton = Design.Button(" Save ")
        self.saveButton.clicked.connect(self.saveButtonPressed)

        self.cancelButton = Design.Button(" Cancel ")
        self.cancelButton.clicked.connect(self.close)

        self.sortListButton = Design.Button("Sort List")
        self.sortListButton.clicked.connect(self.sortListButtonClicked)

        self.listWidget = QtW.QPlainTextEdit()
        self.listWidget.setObjectName("ListInput")
        self.listWidget.setPlainText(", ".join([str(i) for i in self.datalist]))
        self.listWidget.textChanged.connect(self.updateDatalist)

        self.resize(400, 300)

        self.layout().addWidget(
            Design.VBox(
                "write datalist as comma separated values, e.g. '1, 2, 2.5, 3'",
                Design.HBox(self.listWidget),
                Design.HBox(self.sortListButton, 1, self.saveButton, 1, self.cancelButton),
            )
        )

    def updateDatalist(self):
        text = self.listWidget.toPlainText()
        try:
            self.datalist = [self.interpreteToken(token.strip()) for token in text.split(",") if token.strip() != ""]
            self.saveButton.setEnabled(True)
        except Exception:
            self.saveButton.setEnabled(False)

    def interpreteToken(self, token):
        try:
            return int(token)
        except Exception:
            return float(token)

    def saveButtonPressed(self):
        self.callback(self.datalist)
        self.close()

    def sortListButtonClicked(self):
        self.datalist.sort()
        self.listWidget.setPlainText(", ".join([str(i) for i in self.datalist]))
