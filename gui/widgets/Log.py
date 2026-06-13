import json
import traceback
from enum import Enum

import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW
from playsound import playsound

import gui.settings as settings
import gui.widgets.Design as Design
import gui.widgets.Dock as Dock
import gui.widgets.Viewer as Viewer

dock = None


def updateColors():
    if dock is not None:
        for row in range(dock.model.rowCount()):
            dock.model.item(row).updateColors()
            for subrow in range(dock.model.item(row).rowCount()):
                dock.model.item(row).child(subrow).updateColors()


class Level(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


class View(Dock.Dock):
    # creates the viewable interface, only handles very simple logic
    def __init__(self, gui):
        Dock.Dock.__init__(self, "📜 Log", gui)
        global dock
        dock = self

        # create MVC classes
        self.model = Model(self)
        self.controller = Controller(self, self.model)
        self.model.controller = self.controller

        # clear log button
        clearButton = Design.Button("🧹", size="medium")
        clearButton.clicked.connect(lambda: self.model.clearLog())

        self.setRightWidget(clearButton)

        # log
        self.treeView = QtW.QTreeView()
        self.treeView.setFrameShape(QtW.QFrame.Shape.NoFrame)
        self.treeView.setModel(self.model)
        self.treeView.setHeaderHidden(True)  # hides header that defaults to displaying "1"

        # rightclick copy to clip
        self.treeView.setContextMenuPolicy(QtC.Qt.ContextMenuPolicy.ActionsContextMenu)
        copy_action = QtG.QAction("Copy entry to clipboard", self.treeView)
        copy_action.triggered.connect(lambda: Controller.copyToClip(self.treeView.selectedIndexes()[0]))
        show_in_viewer_action = QtG.QAction("Show in viewer", self.treeView)
        show_in_viewer_action.triggered.connect(lambda: Controller.showInViewer(self.treeView.selectedIndexes()[0]))
        self.treeView.addAction(copy_action)
        self.treeView.addAction(show_in_viewer_action)

        self.setWidget(self.treeView)


class Model(QtG.QStandardItemModel):
    # holds the data (here its interwoven with the model that Qt provides)
    class StandardItem(QtG.QStandardItem):
        def __init__(self, txt, level):
            super().__init__()
            self.level = level
            self.setEditable(False)
            self.setText(txt)
            self.setFont(QtG.QFont("Courier New", 10))
            self.updateColors()

        def updateColors(self):
            darkMode = settings.getDarkmode()
            if darkMode:
                if self.level == Level.DEBUG:
                    self.setBackground(QtG.QBrush(QtG.QColor(0, 0, 30, 255)))
                elif self.level == Level.INFO:
                    self.setBackground(QtG.QBrush(QtG.QColor(0, 0, 0, 255)))
                elif self.level == Level.WARNING:
                    self.setBackground(QtG.QBrush(QtG.QColor(30, 30, 0, 255)))
                elif self.level == Level.ERROR:
                    self.setBackground(QtG.QBrush(QtG.QColor(30, 0, 0, 255)))
            else:
                if self.level == Level.DEBUG:
                    self.setBackground(QtG.QBrush(QtG.QColor(244, 244, 255, 255)))
                elif self.level == Level.INFO:
                    self.setBackground(QtG.QBrush(QtG.QColor(255, 255, 255, 255)))
                elif self.level == Level.WARNING:
                    self.setBackground(QtG.QBrush(QtG.QColor(255, 255, 200, 255)))
                elif self.level == Level.ERROR:
                    self.setBackground(QtG.QBrush(QtG.QColor(255, 200, 200, 255)))

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.root = self.invisibleRootItem()

    def addEntry(self, text, level):
        lines = text.split("\n")
        item = Model.StandardItem(lines[0], level)
        item.setToolTip(lines[0])
        self.root.appendRow(item)
        # multiline text gets added as children of the first line
        for i in range(1, len(lines)):
            childItem = Model.StandardItem(lines[i], level)
            childItem.setToolTip(lines[0])
            item.appendRow(childItem)

    def clearLog(self):
        self.root.removeRows(0, self.rowCount())


class Controller:
    # handles all the logic
    def __init__(self, view, model):
        self.view = view
        self.model = model
        Controller.controller = self

    def addLog(self, message, level):
        if level == Level.ERROR and settings.getErrorSoundOn():
            playsound("resources/sounds/error.wav", False)
        scrollToBottom = False
        # if log is scrolled to the bottom, stay at bottom after insert
        if self.view is not None and self.view.treeView is not None and self.view.treeView.verticalScrollBar().value() == self.view.treeView.verticalScrollBar().maximum():
            scrollToBottom = True
        self.model.addEntry(message.__str__(), level)
        if self.view is not None and self.view.treeView is not None and scrollToBottom:
            self.view.treeView.scrollToBottom()

    def getTextFromIndex(index):
        # copy treeview element and all its children to the clipboard
        text = index.model().itemFromIndex(index).text()
        for i in range(index.model().itemFromIndex(index).rowCount()):
            text += "\n" + index.model().itemFromIndex(index).child(i).text()
        return text

    def copyToClip(index):
        QtW.QApplication.clipboard().setText(Controller.getTextFromIndex(index))

    def showInViewer(index):
        Viewer.Dialog(Controller.getTextFromIndex(index)).exec()


def log(*args):
    if len(args) == 0:
        return
    level = Level.INFO
    message = ""
    for arg in args:
        if isinstance(arg, Level):
            level = arg
            continue
        if isinstance(arg, Exception):
            level = Level.ERROR
            arg = f"""{type(arg).__name__}: {str(arg)}\n{traceback.format_exc()}"""
        if type(arg) is not str:
            if type(arg) is dict:
                arg = json.dumps(arg, indent=4)
            else:
                arg = str(arg)
        if "error" in arg.split("\n")[0].lower():
            level = Level.ERROR
        message += arg.replace("\\n", "\n") + "\n"
    while message.endswith("\n"):
        message = message[:-1]
    # wrapper for easier access
    if hasattr(Controller, "controller") and Controller.controller is not None:
        Controller.controller.addLog(message, level)
