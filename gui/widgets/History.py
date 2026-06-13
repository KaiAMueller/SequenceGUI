import PySide6.QtWidgets as QtW

import gui.widgets.Dock as Dock

dock = None


def updateText(undoStack, redoStack):
    richText = ""
    for action in undoStack:
        richText += f"{action['description']}<br>"
    richText += "🧙<br>"
    for i in range(len(redoStack)):
        richText += f"{redoStack[len(redoStack) - i - 1]['description']}<br>"
    dock.textEdit.setHtml(richText)


class Dock(Dock.Dock):
    def __init__(self, gui):
        super(Dock, self).__init__("📜 History", gui)
        global dock
        dock = self
        self.textEdit = QtW.QTextEdit()
        self.textEdit.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.textEdit.setReadOnly(True)
        self.setWidget(self.textEdit)
