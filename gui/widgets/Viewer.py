import json

import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.widgets.Design as Design


class InfoButton(Design.IconButton):
    def __init__(self, data):
        super(InfoButton, self).__init__("📎", lambda: Dialog(data).exec())


class Dialog(Design.DialogDesign):
    def __init__(self, data):
        super(Dialog, self).__init__(title="📎 Viewer")
        self.viewer = Viewer(data)
        self.layout().addWidget(self.viewer)

        # resize gripper
        self.resizeGripper = QtW.QSizeGrip(self)
        self.resizeGripper.setFixedSize(20, 20)
        self.layout().addWidget(
            self.resizeGripper,
            0,
            QtC.Qt.AlignmentFlag.AlignBottom | QtC.Qt.AlignmentFlag.AlignRight,
        )

        screen = QtW.QApplication.primaryScreen()
        workingArea = screen.availableGeometry()
        self.setMaximumWidth(workingArea.width())
        self.setMaximumHeight(workingArea.height())

        # fit to content
        self.resize(self.viewer.sizeHint())


class Viewer(Design.HBox):
    def __init__(self, data):
        text = data if type(data) is str else json.dumps(data, indent=4)
        # super(Viewer, self).__init__(text.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>"))
        self.textEdit = QtW.QPlainTextEdit(text)
        lineCount = len(text.split("\n"))
        self.lineCounterTextEdit = QtW.QPlainTextEdit(self.lineCounter(lineCount))
        super(Viewer, self).__init__(self.lineCounterTextEdit, self.textEdit, spacing=0)

        self.textEdit.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.textEdit.setFont(QtG.QFont("Consolas", 10))
        self.textEdit.setReadOnly(True)
        self.textEdit.setWordWrapMode(QtG.QTextOption.WrapMode.NoWrap)
        self.textEdit.viewport().installEventFilter(self)

        self.lineCounterTextEdit.setObjectName("lineCounterTextEdit")
        self.lineCounterTextEdit.setReadOnly(True)
        self.lineCounterTextEdit.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.lineCounterTextEdit.setFont(QtG.QFont("Consolas", 10))
        self.lineCounterTextEdit.setWordWrapMode(QtG.QTextOption.WrapMode.NoWrap)
        self.lineCounterTextEdit.setFixedWidth((1 + len(str(lineCount))) * self.lineCounterTextEdit.fontMetrics().boundingRect("A").width())
        self.lineCounterTextEdit.setVerticalScrollBarPolicy(QtC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lineCounterTextEdit.setHorizontalScrollBarPolicy(QtC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lineCounterTextEdit.setFocusPolicy(QtC.Qt.FocusPolicy.NoFocus)
        self.lineCounterTextEdit.setTextInteractionFlags(QtC.Qt.TextInteractionFlag.NoTextInteraction)
        self.lineCounterTextEdit.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.textEdit.viewport() and type(event) is QtG.QPaintEvent:
            self.lineCounterTextEdit.verticalScrollBar().setValue(self.textEdit.verticalScrollBar().value())
        elif obj == self.lineCounterTextEdit.viewport() and type(event) is QtG.QWheelEvent:
            return True
        return False

    def sizeHint(self):
        text = self.textEdit.toPlainText()
        # find size
        width = 0
        for line in text.split("\n"):
            w = self.textEdit.fontMetrics().boundingRect(line).width()
            if w > width:
                width = w
        width += self.textEdit.fontMetrics().boundingRect("AAAAAAAA").width()
        width = int(width * 1.1)
        height = self.textEdit.fontMetrics().boundingRect("A").height() * (text.count("\n") + 6)
        height = int(height * 1.1)
        return QtC.QSize(width, height)

    def lineCounter(self, lineCount):
        highestSpaceNumber = len(str(lineCount))
        text = ""
        for i in range(lineCount):
            spaces = " " * (highestSpaceNumber - len(str(i + 1)))
            text += f"{spaces}{i + 1}\n"
        return text
