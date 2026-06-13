import random

import numpy as np
import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.DirectoryList as DirectoryList
import gui.crate.FileManager as FileManager


class Dock(QtW.QDockWidget):
    def __init__(self, title, gui):
        self.title = title
        self.gui = gui
        super(Dock, self).__init__(self.title)
        self.setFeatures(QtW.QDockWidget.DockWidgetFeature.DockWidgetClosable | QtW.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.closeButton = Design.CloseButton(red=False)
        self.closeButton.clicked.connect(self.close)
        self.titleLabel = QtW.QLabel(self.title)
        self.leftWidget = QtW.QWidget()
        self.rightWidget = QtW.QWidget()
        self.settingsButton = QtW.QWidget()
        self.settingsMenu = None
        self.updateTitleBar()
        self.configWidgets = {}
        self.installEventFilter(self)

    def setLeftWidget(self, widget):
        self.leftWidget = widget
        self.updateTitleBar()

    def setRightWidget(self, widget):
        self.rightWidget = widget
        self.updateTitleBar()

    def addSettingsAction(self, text, callback, default=False, checkable=True):
        if self.settingsMenu is None:
            self.settingsMenu = Design.Menu([])
            self.settingsButton = Design.Button(" ⚙️ ")
            self.settingsButton.setCheckable(True)
            self.settingsButton.mousePressEvent = self.openSettingsMenu
            self.settingsMenu.hideEvent = lambda event: QtC.QTimer.singleShot(20, lambda: self.settingsButton.setChecked(False))
            self.updateTitleBar()
        if checkable:
            action = Design.CheckableAction(text, callback, default)
        else:
            action = Design.Action(text, callback)
        self.settingsMenu.addAction(action)
        self.configWidgets[text] = action

    def openSettingsMenu(self, event):
        self.settingsButton.setChecked(not self.settingsButton.isChecked())
        if self.settingsButton.isChecked():
            self.settingsMenu.exec(self.settingsButton.mapToGlobal(QtC.QPoint(0, self.settingsButton.height())))

    def updateTitleBar(self):
        self.setTitleBarWidget(
            Design.HBox(
                self.titleLabel,
                self.leftWidget,
                Design.Spacer(),
                self.rightWidget,
                self.settingsButton,
                self.closeButton,
                spacing=0,
            )
        )

    def configChange(self, option, value):
        self.configWidgets[option].set(value)

    def eventFilter(self, obj: QtC.QObject, event: QtC.QEvent) -> bool:
        if event.type() == QtC.QEvent.Type.MouseButtonRelease:
            self.customMouseReleaseEvent(event)
        return super().eventFilter(obj, event)

    def customMouseReleaseEvent(self, event: QtG.QMouseEvent):
        pos = self.mapToGlobal(event.position()).toPoint()
        for window in self.gui.windows:
            if window.geometry().contains(pos):
                tab = window.getCurrentTab()
                if self in tab.children():
                    for tabName, button in window.tabBar.tabButtons.items():
                        if QtC.QRect(window.tabBar.mapToGlobal(button.pos()), button.size()).contains(pos):
                            QtC.QTimer.singleShot(20, lambda: self.moveToTab(self.gui.tabs[tabName]))
                            return
                    continue
                QtC.QTimer.singleShot(20, lambda: self.moveToTab(tab))
                return

    def moveToTab(self, tab):
        if self in tab.children():
            return
        tab.addDockWidget(QtC.Qt.DockWidgetArea.LeftDockWidgetArea, self)


class ListConfigDockExtension(Dock):
    def __init__(
        self,
        title,
        gui,
        widgetClass,
        itemKind,
        backendCallbacks,
        icon="",
        listClass=None,
    ):
        super(ListConfigDockExtension, self).__init__(title, gui)
        self.widgetClass = widgetClass
        self.itemKind = itemKind
        self.backendCallbacks = backendCallbacks
        self.icon = icon
        self.list = listClass() if listClass is not None else DirectoryList.DirectoryList(self, itemKind)
        self.list.onSelectionChanged = self.changeSelection
        self.list.onItemRightPressed = self.openListItemContextMenu
        self.list.itemGotMoved = self.backendCallbacks.Rename
        self.configWidgetArea = QtW.QScrollArea()
        self.configWidgetArea.setWidgetResizable(True)
        self.configWidgetArea.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.configWidget = None
        self.setCurrentConfigWidget(None)
        self.configWidgetArea.setWidget(self.configWidget)

        self.addButton = Design.Button("➕")
        self.addButton.setToolTip(f"Add a new {self.itemKind} or Directory")
        self.listArea = Design.VBox(1, self.list, Design.HBox(self.addButton, Design.Spacer()))

        self.setWidget(
            Design.Splitter(
                [
                    self.listArea,
                    Design.Frame(self.configWidgetArea, margins=(5, 5, 5, 5)),
                ],
                [0.25, 0.75],
            )
        )
        self.addButton.clicked.connect(self.addButtonClicked)

    def addButtonClicked(self):
        self.openAddItemMenu(self.addButton.mapToGlobal(QtC.QPoint(0, self.addButton.height())))

    def openAddItemMenu(self, pos):
        actions = [
            Design.Action("📁 New Directory", lambda: self.addDirButtonClicked()),
            Design.Action(f"{self.icon} New {self.itemKind}", lambda: self.addItemButtonClicked()),
        ]
        Design.Menu(actions).exec(pos)

    def loadCrate(self, iterable):
        # clear all items
        for itemName in list(self.list.items.keys()):
            self.deleteItem(itemName)

        # add all items
        for itemName, itemData in iterable.items():
            self.addItem(itemName, initialLoad=True, isDir=itemData["isDir"])

        self.list.sortItems()
        self.list.visiblityToAllDirsClosed()

    def addItemButtonClicked(self):
        name = util.textToIdentifier(Design.inputDialog(f"{self.itemKind} name", f"Enter a name for the {self.itemKind}"))
        if name is None or name == "":
            return None
        if name in self.list.items:
            Design.errorDialog("Error", f'{self.itemKind} "{name}" already exists.')
            return None
        if hasattr(self, "additionalNameCheck"):
            if not self.additionalNameCheck(name):
                return None
        self.backendCallbacks.Add(name, {"isDir": False})

    def addDirButtonClicked(self):
        name = util.textToIdentifier(Design.inputDialog("Directory name", "Enter a name for the directory"))
        if name is None or name == "":
            return None
        if name in self.list.items:
            Design.errorDialog("Error", f'"{name}" already exists.')
            return None
        if hasattr(self, "additionalNameCheck"):
            if not self.additionalNameCheck(name):
                return None
        self.backendCallbacks.Add(name, {"isDir": True})

    def addItem(self, name, widgetClass=None, initialLoad=False, isDir=False):
        if name is None or name == "":
            return None
        self.list.add(name, icon="📁" if isDir else self.icon, isDir=isDir)
        if not initialLoad:
            self.list.sortItems()

    def extraContextMenuActions(self, itemName):
        return []

    def openListItemContextMenu(self, itemName, globalPos):
        actions = [
            Design.Action("Rename", lambda: self.renameActionClicked(itemName)),
            Design.Action("Delete", lambda: self.deleteActionClicked(itemName)),
            Design.Action("Save", lambda: self.saveActionClicked(itemName)),
        ]
        actions.extend(self.extraContextMenuActions(itemName))
        Design.Menu(actions).exec(globalPos)

    def renameActionClicked(self, itemName):
        newName = util.textToIdentifier(Design.inputDialog(f"Rename {self.itemKind}", "New Name", itemName.split("/")[-1]))
        path = "/".join(itemName.split("/")[:-1])
        newName = newName if path == "" else path + "/" + newName
        if newName is None or newName == "":
            return
        if newName in self.list.items:
            Design.errorDialog("Error", f'{self.itemKind} "{newName}" already exists.')
            return
        self.backendCallbacks.Rename(itemName, newName)

    def deleteActionClicked(self, itemName):
        if not self.list.checkIfDirEmpty(itemName):
            Design.errorDialog(
                "Error",
                f'Directory "{itemName}" is not empty. Please delete or move out all items in the directory first.',
            )
            return
        if itemName is not None:
            if Design.confirmationDialog(
                f"Delete {self.itemKind}",
                f'Are you sure you want to delete the {self.itemKind} "{itemName}"?',
            ):
                self.backendCallbacks.Delete(itemName)
                
    def saveActionClicked(self, itemName):
        #Not implemented
        if not self.list.checkIfDirEmpty(itemName):
            Design.errorDialog(
                "Error",
                f'Directory "{itemName}" is not empty. Please delete or move out all items in the directory first.',
            )
            return
        if itemName is not None:
            FileManager.saveSequenceData(itemName)
 
                

    def deleteItem(self, name):
        # update list
        self.list.remove(name)

        # delete config widget
        if self.configWidget is not None:
            if name == self.configWidget.name:
                self.setCurrentConfigWidget(None)
        

    def getWidgetClass(self, newSelection):
        return self.widgetClass

    def changeSelection(self, newSelection):
        if newSelection is None:
            self.setCurrentConfigWidget(None)
        else:
            widgetClass = self.getWidgetClass(newSelection)
            if widgetClass is None:
                return
            self.setCurrentConfigWidget(widgetClass(newSelection, self))
        self.list.setCurrentSelection(newSelection, silent=True)

    def setCurrentConfigWidget(self, configWidget):
        if self.configWidget is not None:
            self.configWidget.deleteLater()
        self.configWidget = configWidget
        self.configWidgetArea.setWidget(self.configWidget if self.configWidget is not None else EmptyConfigWidget())

    def renameItem(self, oldName, newName):
        # update list
        self.list.moveItem(oldName, newName)

    def widgetValueChange(self, name, valueName, value):
        if self.configWidget is not None and name == self.configWidget.name:
            self.configWidget.valueChange(valueName, value)


class EmptyConfigWidget(Design.HintText):
    def __init__(self):
        super(EmptyConfigWidget, self).__init__("Nothing selected", alignment=QtC.Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("EmptyConfigWidget")
        self.fireWorks = []

    def contextMenuEvent(self, ev: QtG.QContextMenuEvent):
        menu = QtW.QMenu()
        boredMenu = menu.addMenu("Make BEC Happen?")
        boredMenu.addAction("Yes", self.BECMagic)
        boredMenu.addAction("No", lambda: self.setText("😭"))
        menu.addMenu(boredMenu)
        menu.exec(ev.globalPos())

    def BECMagic(self):
        self.launchFireworks(self.mapFromGlobal(QtG.QCursor.pos()))
        self.setText("🧙🪄 Simsalabim, BEC success rate increased by 69^(-420) %")

    def setText(self, text):
        self.setFont(QtG.QFont("Arial", 20))
        super().setText(text)

    def launchFireworks(self, pos):
        x = pos.x()
        y = pos.y()
        for i in range(100):
            angle = random.uniform(0, 2 * 3.14159265)
            velocity = np.sqrt(random.uniform(0, 15))
            firework = {
                "x": x,
                "y": y,
                "dx": velocity * np.cos(angle),
                "dy": velocity * np.sin(angle),
                "color": QtG.QColor(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                ),
            }
            self.fireWorks.append(firework)
        QtC.QTimer.singleShot(20, self.updateFireworks)

    def updateFireworks(self):
        for firework in list(self.fireWorks):
            firework["x"] += firework["dx"]
            firework["y"] += firework["dy"]
            firework["dy"] += 0.2
            if firework["y"] > self.height():
                self.fireWorks.remove(firework)
        self.repaint()
        if len(self.fireWorks) > 0:
            QtC.QTimer.singleShot(20, self.updateFireworks)

    def paintEvent(self, e: QtG.QPaintEvent):
        painter = QtG.QPainter(self)
        for firework in self.fireWorks:
            painter.setPen(QtG.QPen(QtG.QColor(0, 0, 0), 1))
            painter.setBrush(QtG.QBrush(firework["color"]))
            painter.drawEllipse(int(firework["x"]), int(firework["y"]), 5, 5)
        super().paintEvent(e)
