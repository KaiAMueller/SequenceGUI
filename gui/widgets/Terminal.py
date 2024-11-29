import datetime
import queue

import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW

import gui.widgets.Design as Design
import gui.widgets.Dock

dock = None
title = "🐍 Python Console"
printQueue = queue.SimpleQueue()
localExecuteMemory = {}


def terminalPrint(*args, **kwargs):
    __builtins__["oldprint"](*args, **kwargs)
    global printQueue
    printQueue.put((args, kwargs))


# override print
__builtins__["oldprint"] = __builtins__["print"]
__builtins__["print"] = terminalPrint


def executeLine(line):
    global localExecuteMemory
    try:
        print(eval(line, {}, localExecuteMemory))
    except Exception:
        try:
            exec(line, {}, localExecuteMemory)
        except Exception as e:
            print(e)


class Dock(gui.widgets.Dock.Dock):
    def __init__(self, gui):
        super(Dock, self).__init__(title, gui)
        global dock
        dock = self
        self.textEdit = QtW.QPlainTextEdit()
        self.textEdit.setLineWrapMode(QtW.QPlainTextEdit.LineWrapMode.NoWrap)
        self.textEdit.setCenterOnScroll(True)
        self.textEdit.setFont(Design.ValueFont())
        self.textEdit.setReadOnly(True)

        self.lineEdit = QtW.QLineEdit()
        self.lineEdit.setFont(Design.ValueFont())
        self.lineEdit.returnPressed.connect(self.lineEditReturnPressed)

        self.setWidget(Design.VBox(self.textEdit, self.lineEdit))

        QtC.QTimer.singleShot(100, self.queueLoop)

    def lineEditReturnPressed(self):
        print(self.lineEdit.text())
        executeLine(self.lineEdit.text())
        self.lineEdit.setText("")

    def queueLoop(self):
        while True:
            try:
                args, kwargs = printQueue.get(block=False)
                time = datetime.datetime.now().strftime("%H:%M:%S")
                self.appendPlainText(f"{time}> " + " ".join([str(arg) for arg in args]))
            except queue.Empty:
                break
        QtC.QTimer.singleShot(100, self.queueLoop)

    def appendPlainText(self, text):
        self.textEdit.appendPlainText(text)
