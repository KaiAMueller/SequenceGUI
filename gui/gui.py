import ctypes
import os
from datetime import datetime

import git
import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.crate.Versioneer as Versioneer
import gui.settings as settings
import gui.widgets.Camera as Camera
import gui.widgets.Dashboard as Dashboard
import gui.widgets.Design as Design
import gui.widgets.Git as Git
import gui.widgets.History as History
import gui.widgets.Input as Input
import gui.widgets.LabSetup as LabSetup
import gui.widgets.Log as Log
import gui.widgets.MultiRun as MultiRun
import gui.widgets.Playlist as Playlist
import gui.widgets.RPC as RPC
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.TableSequenceView as TableSequenceView
import gui.widgets.Terminal as Terminal
import gui.widgets.Variables as Variables
from gui.widgets.Log import log

DOCKS = {
    "Log": {
        "class": Log.View,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "SequenceEditor": {
        "class": SequenceEditor.Dock,
        "area": QtC.Qt.DockWidgetArea.TopDockWidgetArea,
        "needLoad": True,
    },
    "LabSetup": {
        "class": LabSetup.Dock,
        "area": QtC.Qt.DockWidgetArea.TopDockWidgetArea,
        "needLoad": True,
    },
    "RPC": {
        "class": RPC.Dock,
        "area": QtC.Qt.DockWidgetArea.TopDockWidgetArea,
        "needLoad": True,
    },
    "Camera": {
        "class": Camera.View,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "Git": {
        "class": Git.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "MultiRun": {
        "class": MultiRun.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": True,
    },
    "Variables": {
        "class": Variables.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": True,
    },
    "History": {
        "class": History.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "Terminal": {
        "class": Terminal.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "TableSequenceView": {
        "class": TableSequenceView.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "Dashboard": {
        "class": Dashboard.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
    "Playlist": {
        "class": Playlist.Dock,
        "area": QtC.Qt.DockWidgetArea.BottomDockWidgetArea,
        "needLoad": False,
    },
}

DEFAULT_TABIFIY_DOCKS = [
    ["LabSetup", "RPC"],
    [
        "Log",
        "Terminal",
        "History",
        "Variables",
        "MultiRun",
        "Git",
        "Camera",
        "Dashboard",
        "Playlist",
    ],
]


class Gui:
    def __init__(self, app, eventLoop, exit_request):
        self.app = app
        self.eventLoop = eventLoop
        self.exit_request = exit_request
        self.tabs = {}
        self.docks = {}
        self.windows = []
        crate.Config.init()

        window = self.createWindow()
        self.loadDocks(window)

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SequenceGUI")
        except Exception:
            pass
        if "maximized" in settings.data["layout"] and "geometry" in settings.data["layout"]:
            if settings.data["layout"]["maximized"]:
                window.restoreGeometry(bytes.fromhex(settings.data["layout"]["geometry"]))
                window.showMaximized()
            else:
                window.showNormal()
                window.restoreGeometry(bytes.fromhex(settings.data["layout"]["geometry"]))
        else:
            window.showMaximized()
        crate.FileManager.startAutosaveLoop()
        log("started on {}".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        self.loadCrate()
        settings.setChangeCrate(False)

    def createWindow(self):
        window = GuiWindow(self)
        self.windows.append(window)
        return window

    def closeAllWindows(self):
        for window in list(self.windows):
            window.close()

    def onCloseWindow(self, window):
        if len(self.windows) == 1:
            crate.FileManager.exitFlag = True
            crate.FileManager.joinAutosaveLoop()
            RPC.dock.stopWatchdogObserver()
            self.exit_request.set()
        self.windows.remove(window)

    def loadDocks(self, window):
        if "layout" not in settings.data:
            settings.data["layout"] = {}
        layout = settings.data["layout"]
        if "state" in layout or "tabs" not in layout:  # old version
            layout["tabs"] = {"main": {"docks": list(DOCKS.keys()), "state": None}}

        for tabName, tabData in layout["tabs"].items():
            window.addTab(tabName)
            tab = self.tabs[tabName]
            for dockName in tabData["docks"]:
                if dockName in DOCKS:
                    self.loadDockToTab(dockName, tab)

            if tabData["state"] is not None:
                tab.restoreState(bytes.fromhex(tabData["state"]))
            else:
                for tabifyDocks in DEFAULT_TABIFIY_DOCKS:
                    if tabifyDocks[0] not in self.docks:
                        continue
                    for i in range(1, len(tabifyDocks)):
                        if tabifyDocks[i] not in self.docks:
                            continue
                        tab.tabifyDockWidget(self.docks[tabifyDocks[0]], self.docks[tabifyDocks[i]])
                    self.docks[tabifyDocks[0]].raise_()
        allLoadedDocks = []
        for tabData in layout["tabs"].values():
            allLoadedDocks += tabData["docks"]
        for dockName in DOCKS:
            if dockName not in allLoadedDocks:
                self.loadDockToTab(dockName, window.stackedWidget.currentWidget())

    def loadDockToTab(self, dockName, tab):
        dock = DOCKS[dockName]["class"](self)
        dock.setObjectName(dockName)
        tab.addDockWidget(DOCKS[dockName]["area"], dock)
        self.docks[dockName] = dock

    def loadCrate(self):
        crate.loadDone = False
        Versioneer.checkUpdate()
        for dock in DOCKS:
            if DOCKS[dock]["needLoad"]:
                self.docks[dock].loadCrate()
        crate.loadDone = True
        TableSequenceView.updateTable()
        log("Crate loaded")

    def updateAppearance(self, darkmode):
        settings.setDarkmode(darkmode)
        TableSequenceView.updateTable()


class GuiWindow(QtW.QMainWindow):
    def __init__(self, gui):
        super(GuiWindow, self).__init__()
        self.gui = gui
        self.setObjectName("gui")

        self.mouseCursorOverriden = False
        self.mouseOnBorder = 0
        self.mouseResizeDragPos = None
        self.maximized = True

        # Make Window Frameless
        self.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
        self.setContentsMargins(0, 0, 0, 0)

        # Set Icon
        if "icon" not in crate.config:
            crate.config["icon"] = os.getcwd() + "/resources/images/default_icon.png"
        iconPath = crate.config["icon"]
        if iconPath is None or not os.path.isfile(iconPath):
            iconPath = os.getcwd() + "/resources/images/default_icon.png"
        self.icon = QtG.QIcon(iconPath)
        self.setWindowIcon(self.icon)

        self.iconLabel = QtW.QLabel()
        self.iconLabel.setPixmap(self.icon.pixmap(24, 24))

        self.crateButton = Design.Button("SequenceGUI", size="medium")
        self.crateButton.setObjectName("crateButton")

        self.crateMenu = QtW.QMenu(self.crateButton.text())
        self.crateButton.setMenu(self.crateMenu)

        self.undoAction = self.crateMenu.addAction("Undo")
        self.undoAction.triggered.connect(crate.undo)
        self.undoAction.setShortcut(QtG.QKeySequence(QtC.Qt.Key.Key_Z | QtC.Qt.KeyboardModifier.ControlModifier))
        self.undoAction.setEnabled(False)
        self.redoAction = self.crateMenu.addAction("Redo")
        self.redoAction.triggered.connect(crate.redo)
        self.redoAction.setShortcut(QtG.QKeySequence(QtC.Qt.Key.Key_Y | QtC.Qt.KeyboardModifier.ControlModifier))
        self.redoAction.setEnabled(False)

        self.crateMenu.addSeparator()

        self.openCrateAction = self.crateMenu.addAction("Open in File Explorer")
        self.openCrateAction.triggered.connect(crate.FileManager.openCrateInFileExplorer)

        self.changeCrateAction = self.crateMenu.addAction("Close and Change Crate")
        self.changeCrateAction.triggered.connect(self.changeCrate)

        self.settingsAction = self.crateMenu.addAction("Settings")
        self.settingsAction.triggered.connect(self.openSettings)

        self.viewAction = self.crateMenu.addAction("View")
        self.viewAction.triggered.connect(self.openView)

        self.aboutAction = self.crateMenu.addAction("About")
        self.aboutAction.triggered.connect(self.openAbout)

        self.tabBar = TabBar(self)
        self.tabBar.onTabChanged = self.tabChanged

        self.addTabButton = Design.Button("➕")
        self.addTabButton.setFixedSize(MenuBar.HEIGHT, MenuBar.HEIGHT)
        self.addTabButton.clicked.connect(self.addTabButtonClicked)

        self.tabArea = Design.HBox(self.tabBar, self.addTabButton, spacing=0)
        self.tabArea.setFixedHeight(MenuBar.HEIGHT)

        self.iconLabelAndNameAndMenus = Design.HBox(self.iconLabel, self.crateButton, self.tabArea, spacing=0)

        versionNr = crate.config["version"] if "version" in crate.config else ""
        gitRepo = git.Repo(os.getcwd())
        self.versionText = Design.HintText(f"{versionNr} {gitRepo.active_branch.name} {gitRepo.head.commit.hexsha[:7]}")
        self.versionText.setWordWrap(False)
        self.minimizeButton = Design.Button("🗕", size="large")
        self.minimizeButton.setFixedHeight(MenuBar.HEIGHT)
        self.minimizeButton.clicked.connect(self.showMinimized)
        self.maximizeButton = Design.Button("🗖", size="large")
        self.maximizeButton.setFixedHeight(MenuBar.HEIGHT)
        self.maximizeButton.clicked.connect(self.toggleMaximized)
        self.closeButton = Design.CloseButton()
        self.closeButton.setText("  🞪  ")
        self.closeButton.setFixedHeight(MenuBar.HEIGHT)
        self.closeButton.clicked.connect(self.close)

        self.windowControls = Design.HBox(
            self.versionText,
            self.minimizeButton,
            self.maximizeButton,
            self.closeButton,
            spacing=0,
        )

        self.menuBar = MenuBar(self)

        self.menuBar.setWidgetArea(self.iconLabelAndNameAndMenus, "left")
        self.menuBar.setWidgetArea(self.windowControls, "right")

        self.stackedWidget = QtW.QStackedWidget()
        self.stackedWidget.setObjectName("tabStackedWidget")
        self.setCentralWidget(Design.VBox(self.menuBar, self.stackedWidget, spacing=0))

        self.setWindowTitle("SequenceGUI")

    def openSettings(self):
        settings.Dialog(self.gui).exec()

    def openView(self):
        self.getCurrentTab().contextMenuEvent(QtG.QContextMenuEvent(QtG.QContextMenuEvent.Reason.Mouse, QtC.QPoint(0, 0)))

    def openAbout(self):
        dialog = Design.DialogDesign("About", "🛈")
        text = """

SequenceGUI is a graphical user interface for
running the Artiq experiment control system.
        
This project is GPLv3 licensed.

Copyright © 2024

German Aerospace Center (DLR)
Insitute for Satellite Geodesy and Inertial Sensing (SI)

Leibniz University Hannover (LUH)
Insitute of Quantum Optics (IQO)

QVLS-iLabs as part of the initiative
“Clusters4Future” is funded by the
Federal Ministry of Education and Research (BMBF)
(Grant No. 03ZU1209IB).

Part of this research was funded by the Federal
Ministry for Economic Affairs and Climate
Action (BMWK) due to an enactment of the German
Bundestag under Grant 50NA2106 (QGyro+)
"""
        bmbf_image = QtW.QLabel()
        bmbf_image.setPixmap(QtG.QPixmap(os.getcwd() + "/resources/images/Clusters4Future_Foederlogo_RGB-DEU.PNG"))
        bmwk_image = QtW.QLabel()
        bmwk_image.setPixmap(QtG.QPixmap(os.getcwd() + "/resources/images/bmwk.png"))
        luh_image = QtW.QLabel()
        luh_image.setPixmap(QtG.QPixmap(os.getcwd() + "/resources/images/luh.png"))
        dlr_image = QtW.QLabel()
        dlr_image.setPixmap(QtG.QPixmap(os.getcwd() + "/resources/images/dlr.png"))
        dialog.layout().addWidget(
            Design.HBox(
                Design.VBox(QtW.QLabel(text), Design.Spacer()),
                Design.VBox(dlr_image, luh_image, Design.Spacer()),
            )
        )
        dialog.layout().addWidget(
            Design.HBox(bmbf_image, bmwk_image)
        )
        dialog.exec()

    def getCurrentTab(self):
        return self.stackedWidget.currentWidget()

    def addTabButtonClicked(self):
        tabName = Design.inputDialog("Tab Name", "Enter the name of the new tab")
        if tabName is None:
            return
        if tabName in self.gui.tabs:
            Design.errorDialog("Error", f"Tab {tabName} already exists")
            return
        self.addTab(tabName)

    def addTab(self, tabName):
        if tabName in self.gui.tabs:
            return
        self.gui.tabs[tabName] = Tab(self)
        self.stackedWidget.addWidget(self.gui.tabs[tabName])
        self.tabBar.addTabButton(tabName)

    def tabChanged(self, tabName):
        self.stackedWidget.setCurrentWidget(self.gui.tabs[tabName])

    def updateCrateIcon(self):
        self.icon = QtG.QIcon(crate.config["icon"])
        self.setWindowIcon(self.icon)
        self.iconLabel.setPixmap(self.icon.pixmap(24, 24))

    def toggleMaximized(self):
        if self.maximized:
            self.showNormal()
        else:
            self.showMaximized()

    def changeCrate(self):
        settings.setChangeCrate()
        self.gui.closeAllWindows()

    # overloaded because save layout not working in qt with maximized (qt bug not fixed in pyqt6)
    def showMaximized(self, edge=QtC.Qt.Edge(0), screen=None) -> None:
        self.maximized = True
        if screen is None:
            screen = self.getCurrentScreen()
        workingArea = screen.availableGeometry()
        x = screen.geometry().x()
        y = screen.geometry().y()
        w = workingArea.width()
        h = workingArea.height()
        if edge & QtC.Qt.Edge.LeftEdge:
            w = int(w / 2)
        elif edge & QtC.Qt.Edge.RightEdge:
            x = x + int(w / 2)
            w = int(w / 2)
        if edge & QtC.Qt.Edge.TopEdge:
            h = int(h / 2)
        elif edge & QtC.Qt.Edge.BottomEdge:
            y = y + int(h / 2)
            h = int(h / 2)
        self.resize(w, h)
        self.move(x, y)
        self.setContentsMargins(0, 0, 0, 0)
        self.mouseOnBorder = False
        super().showNormal()

    def showNormal(self, zoomPoint=None, screen=None) -> None:
        self.maximized = False
        screen = self.getCurrentScreen() if screen is None else screen
        workingArea = screen.availableGeometry()
        sx = screen.geometry().x()
        sy = screen.geometry().y()
        w = workingArea.width()
        h = workingArea.height()
        self.resize(int(0.7 * w), int(0.7 * h))
        if zoomPoint is not None:
            x = sx + int((zoomPoint.x() - sx) * 0.3)
            y = sy + int((zoomPoint.y() - sy) * 0.3)
            self.move(x, y)
        else:
            self.move(sx + int(0.15 * w), sy + int(0.15 * h))
        self.setContentsMargins(3, 3, 3, 3)
        super().showNormal()

    def getCurrentScreen(self):
        for screen in self.gui.app.screens():
            if screen.geometry().contains(self.x(), self.y()):
                return screen
        return self.gui.app.primaryScreen()

    def mouseMoveEvent(self, event) -> None:
        if not self.maximized:
            if self.mouseResizeDragPos is None:
                pos = event.pos()
                self.mouseOnBorder = self.onBorderCondition(pos)
                if self.mouseOnBorder:
                    if not self.mouseCursorOverriden:
                        self.mouseCursorOverriden = True
                        QtC.QTimer.singleShot(20, self.checkMouseCursorOverriden)
                    cursor = None
                    if self.mouseOnBorder == 1 or self.mouseOnBorder == 2:
                        cursor = QtC.Qt.CursorShape.SizeHorCursor
                    elif self.mouseOnBorder == 4 or self.mouseOnBorder == 8:
                        cursor = QtC.Qt.CursorShape.SizeVerCursor
                    elif self.mouseOnBorder == 5 or self.mouseOnBorder == 10:
                        cursor = QtC.Qt.CursorShape.SizeFDiagCursor
                    elif self.mouseOnBorder == 6 or self.mouseOnBorder == 9:
                        cursor = QtC.Qt.CursorShape.SizeBDiagCursor
                    if cursor is not None:
                        self.setCursor(cursor)
        return super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if self.mouseOnBorder:
            self.mouseResizeDragPos = event.globalPosition().toPoint()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.mouseResizeDragPos = None
        return super().mouseReleaseEvent(event)

    def checkMouseCursorOverriden(self):
        if self.mouseCursorOverriden:
            QtC.QTimer.singleShot(20, self.checkMouseCursorOverriden)
            pos = self.mapFromGlobal(QtG.QCursor.pos())
            if self.mouseResizeDragPos is None:
                self.mouseOnBorder = self.onBorderCondition(pos)
            if self.mouseOnBorder or self.mouseResizeDragPos is not None:
                if self.mouseResizeDragPos is not None:
                    pos = pos + self.pos()
                    x = self.x()
                    y = self.y()
                    w = self.width()
                    h = self.height()
                    xd = pos.x() - self.mouseResizeDragPos.x()
                    yd = pos.y() - self.mouseResizeDragPos.y()
                    if self.mouseOnBorder & 1:
                        x += xd
                        w -= xd
                    if self.mouseOnBorder & 2:
                        w += xd
                    if self.mouseOnBorder & 4:
                        y += yd
                        h -= yd
                    if self.mouseOnBorder & 8:
                        h += yd
                    self.move(x, y)
                    self.resize(w, h)
                    self.mouseResizeDragPos = pos
            else:
                self.setCursor(QtC.Qt.CursorShape.ArrowCursor)
                self.mouseCursorOverriden = False

    def onBorderCondition(self, pos):
        onLeftBorder = pos.x() < 3
        onRightBorder = pos.x() > self.width() - 3
        onTopBorder = pos.y() < 3
        onBottomBorder = pos.y() > self.height() - 3
        inside = pos.x() >= 0 and pos.y() >= 0 and pos.x() <= self.width() and pos.y() <= self.height()
        return (not self.maximized and inside) * (onLeftBorder + (onRightBorder << 1) + (onTopBorder << 2) + (onBottomBorder << 3))

    def closeEvent(self, e: QtG.QCloseEvent):
        if len(self.gui.windows) > 1:
            # move all tabs to a window thats still alive
            window = self.gui.windows[0] if self.gui.windows[0] != self else self.gui.windows[1]
            self.tabBar.moveAllTabsToOtherWindow(window)
        self.gui.onCloseWindow(self)
        super().closeEvent(e)


class Tab(QtW.QMainWindow):
    def __init__(self, gui):
        super(Tab, self).__init__()
        self.gui = gui
        self.setObjectName("tab")
        self.setContentsMargins(0, 0, 0, 0)
        self.setDockNestingEnabled(True)

    def getDocks(self):
        return {dock.objectName(): dock for dock in self.findChildren(QtW.QDockWidget)}

    def paintEvent(self, e: QtG.QPaintEvent):
        painter = QtG.QPainter(self)
        painter.setBrush(QtG.QBrush(Tab.getColor()))
        painter.setPen(QtC.Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.width(), self.height())
        painter.end()
        return super().paintEvent(e)

    def getColor():
        return QtG.QColor(10, 0, 30, 50 if settings.getDarkmode() else 20)


class TabBar(QtW.QWidget):
    def __init__(self, guiWindow):
        super(TabBar, self).__init__()
        self.guiWindow = guiWindow
        self.setFixedHeight(MenuBar.HEIGHT)
        self.tabButtons = {}
        self.onTabChanged = None
        self.currentTab = None
        self.setLayout(QtW.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

    def paintEvent(self, e: QtG.QPaintEvent):
        if self.currentTab in self.tabButtons:
            painter = QtG.QPainter(self)
            painter.setBrush(QtG.QBrush(Tab.getColor()))
            painter.setPen(QtC.Qt.PenStyle.NoPen)
            x = self.tabButtons[self.currentTab].geometry().x()
            w = self.tabButtons[self.currentTab].geometry().width()
            painter.drawRect(x, 0, w, self.height())
            painter.end()
        return super().paintEvent(e)

    def tabChanged(self, tabName):
        self.currentTab = tabName
        if self.onTabChanged is not None:
            self.onTabChanged(tabName)
        self.repaint()

    def addTabButton(self, tabName):
        if self.currentTab is None:
            self.currentTab = tabName
        self.tabButtons[tabName] = TabButton(tabName, self)
        self.layout().addWidget(self.tabButtons[tabName])

    def buttonContextMenu(self, tabName):
        menu = QtW.QMenu()
        closeAction = menu.addAction("Close")
        closeAction.triggered.connect(lambda: self.closeTabClicked(tabName))
        renameAction = menu.addAction("Rename")
        renameAction.triggered.connect(lambda: self.renameTabClicked(tabName))
        if len(self.tabButtons) == 1:
            closeAction.setEnabled(False)
        menu.exec(QtG.QCursor.pos())

    def closeTabClicked(self, tabName):
        if len(self.tabButtons) == 1:
            return
        tab = self.guiWindow.gui.tabs[tabName]
        if len(tab.getDocks()) > 0:
            Design.errorDialog("Error", "Tab has docks attached. Move them first.")
            return
        self.layout().removeWidget(self.tabButtons[tabName])
        self.tabButtons[tabName].deleteLater()
        del self.tabButtons[tabName]
        self.guiWindow.stackedWidget.removeWidget(tab)
        self.guiWindow.gui.tabs[tabName].deleteLater()
        del self.guiWindow.gui.tabs[tabName]

    def renameTabClicked(self, tabName):
        newName = Input.inputDialog("Rename Tab", "Enter the new name for the tab", defaultText=tabName)
        if newName is None or newName == "":
            return
        if newName in self.tabButtons:
            Design.errorDialog("Error", f"Tab {newName} already exists")
            return
        self.tabButtons[tabName].setText(newName)
        tab = self.guiWindow.gui.tabs[tabName]
        self.guiWindow.gui.tabs[newName] = tab
        del self.guiWindow.gui.tabs[tabName]
        self.tabButtons[newName] = self.tabButtons[tabName]
        del self.tabButtons[tabName]

    def moveTabToOtherWindow(self, tabName, window, doEvenIfLast=False):
        if tabName not in self.tabButtons:
            return
        if window == self.guiWindow:
            return
        if len(self.tabButtons) == 1 and not doEvenIfLast:
            return
        self.layout().removeWidget(self.tabButtons[tabName])
        self.tabButtons[tabName].deleteLater()
        del self.tabButtons[tabName]
        tab = self.guiWindow.gui.tabs[tabName]
        self.guiWindow.stackedWidget.removeWidget(tab)
        window.stackedWidget.addWidget(tab)
        window.tabBar.addTabButton(tabName)

    def moveAllTabsToOtherWindow(self, window):
        for tabName in list(self.tabButtons.keys()):
            self.moveTabToOtherWindow(tabName, window, doEvenIfLast=True)

    def tabGotDraggedOutside(self, tabName, pos: QtC.QPoint):
        if len(self.tabButtons) == 1:
            return
        screen = getCurrentScreenFromGlobalPos(self.guiWindow.gui.app, pos.x(), pos.y())
        window = self.guiWindow.gui.createWindow()
        self.moveTabToOtherWindow(tabName, window)
        if self.guiWindow.maximized:
            window.showMaximized(screen=screen)
        else:
            window.showNormal(screen=screen)


class TabButton(Design.Button):
    def __init__(self, tabName, tabBar):
        self.tabBar = tabBar
        super(TabButton, self).__init__(tabName, size="medium")
        self.setFixedHeight(MenuBar.HEIGHT)
        self.dragStartPos = None
        self.clicked.connect(self.onClicked)
        self.onRightClick = self.onRightClicked

    def onClicked(self):
        self.tabBar.tabChanged(self.text())

    def onRightClicked(self):
        self.tabBar.buttonContextMenu(self.text())

    def mousePressEvent(self, e: QtG.QMouseEvent) -> None:
        self.dragStartPos = e.globalPosition().toPoint()
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, a0: QtG.QMouseEvent) -> None:
        if self.dragStartPos is not None:
            pos = a0.globalPosition().toPoint()
            if (pos - self.dragStartPos).manhattanLength() > 5:
                self.dragStartPos = None
                drag = TabButton.Drag(self)
                mimeData = QtC.QMimeData()
                mimeData.setData("TabButton", self.text().encode())
                drag.setMimeData(mimeData)
                pixmap = QtG.QPixmap(self.size())
                self.render(pixmap)
                drag.setPixmap(pixmap)
                drag.exec(supportedActions=QtC.Qt.DropAction.MoveAction)
        return super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, e: QtG.QMouseEvent) -> None:
        self.dragStartPos = None
        return super().mouseReleaseEvent(e)

    def customDropEvent(self, dock):
        print(dock, "moved to", self.text())

    class Drag(QtG.QDrag):
        def __init__(self, tabButton):
            self.tabButton = tabButton
            super(TabButton.Drag, self).__init__(tabButton)

        def event(self, e: QtC.QEvent):
            if e.type() == QtC.QEvent.Type.DeferredDelete:
                pos = QtG.QCursor.pos()
                windows = self.tabButton.tabBar.guiWindow.gui.windows
                foundWindow = False
                for window in windows:
                    if window.geometry().contains(pos):
                        self.tabButton.tabBar.moveTabToOtherWindow(self.tabButton.text(), window, doEvenIfLast=True)
                        if len(self.tabButton.tabBar.tabButtons) == 0:
                            self.tabButton.tabBar.guiWindow.close()
                        foundWindow = True
                        break
                if not foundWindow:
                    self.tabButton.tabBar.tabGotDraggedOutside(self.tabButton.text(), pos)
            return super().event(e)


class MenuBar(QtW.QWidget):
    HEIGHT = 30

    def __init__(self, guiWindow):
        super().__init__(guiWindow)
        self.guiWindow = guiWindow
        self.startDragOffset = None
        self.startDragSize = None
        self.cornerLayouts = {
            "left": QtW.QWidget(),
            "middle": QtW.QWidget(),
            "right": QtW.QWidget(),
        }
        self.setLayout(QtW.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(
            Design.HBox(
                self.cornerLayouts["left"],
                Design.Spacer(),
                self.cornerLayouts["middle"],
                Design.Spacer(),
                self.cornerLayouts["right"],
                spacing=0,
            )
        )
        self.setFixedHeight(MenuBar.HEIGHT)

    def setWidgetArea(self, widget, corner):
        layout = self.cornerLayouts[corner].layout()
        if layout is None:
            layout = QtW.QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.cornerLayouts[corner].setLayout(layout)
        for w in layout.children():
            layout.removeWidget(w)
            w.deleteLater()
        layout.addWidget(widget)

    # make window draggable
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtC.Qt.MouseButton.LeftButton:
            self.startDragOffset = event.globalPosition().toPoint() - self.guiWindow.pos()
            self.startDragSize = self.guiWindow.size()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.startDragOffset is None:
            super().mouseReleaseEvent(event)
            return
        self.startDragOffset = None

    def mouseMoveEvent(self, event):
        if self.startDragOffset is None:
            super().mouseMoveEvent(event)
            return
        pos = event.globalPosition().toPoint()
        edge = QtC.Qt.Edge(0)
        screen = getCurrentScreenFromGlobalPos(self.guiWindow.gui.app, pos.x(), pos.y())
        screenPos = pos - screen.geometry().topLeft()
        availableGeometry = screen.availableGeometry()
        if screenPos.x() < 5 and screenPos.x() > -1:
            edge = edge | QtC.Qt.Edge.LeftEdge
        elif screenPos.x() > availableGeometry.width() - 5 and screenPos.x() < availableGeometry.width() + 1:
            edge = edge | QtC.Qt.Edge.RightEdge
        if screenPos.y() < 1 and screenPos.y() > -1:
            edge = edge | QtC.Qt.Edge.TopEdge
        elif screenPos.y() > availableGeometry.height() - 5 and screenPos.y() < availableGeometry.height() + 1:
            edge = edge | QtC.Qt.Edge.BottomEdge
        if edge == QtC.Qt.Edge(0):
            if self.guiWindow.maximized:
                self.guiWindow.showNormal(zoomPoint=pos)
                self.startDragSize = self.guiWindow.size()
                self.startDragOffset = event.globalPosition().toPoint() - self.guiWindow.pos()
            else:
                self.guiWindow.move(pos - self.startDragOffset)
                self.guiWindow.resize(self.startDragSize)
        else:
            self.guiWindow.showMaximized(edge, screen)
        event.accept()

    def mouseDoubleClickEvent(self, e):
        super().mouseDoubleClickEvent(e)
        self.guiWindow.toggleMaximized()


def getCurrentScreenFromGlobalPos(app, x, y):
    for screen in app.screens():
        if screen.geometry().contains(x, y):
            return screen
    return app.primaryScreen()
