import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.widgets.Design as Design
import gui.widgets.Dock

dock = None


class Dock(gui.widgets.Dock.Dock):
    def __init__(self, gui):
        super(Dock, self).__init__("🕹 Dashboard", gui)
        global dock
        dock = self

        self.changeModeButton = Design.Button("Edit Mode", size="medium")
        self.changeModeButton.setCheckable(True)
        self.changeModeButton.toggled.connect(self.changeModeToggled)

        self.addItemButton = Design.Button("Add Item ➕", size="medium")
        self.addItemButton.setMenu(self.addItemMenu())
        self.addItemButton.setHidden(True)

        self.enableGridButton = Design.Button("Enable Grid 𝄜", size="medium")
        self.enableGridButton.setCheckable(True)
        self.enableGridButton.toggled.connect(self.enableGridToggled)
        self.enableGridButton.setHidden(True)

        self.setRightWidget(Design.HBox(self.enableGridButton, self.addItemButton, self.changeModeButton))

        self.dashboard = Dashboard()
        self.setWidget(self.dashboard)
        self.setMouseTracking(True)

    def changeModeToggled(self, checked):
        self.dashboard.editMode = checked
        self.addItemButton.setHidden(not checked)
        self.enableGridButton.setHidden(not checked)
        for child in self.dashboard.children():
            if isinstance(child, Item):
                child.setEnabled(not checked)
        self.repaint()

    def enableGridToggled(self, checked):
        self.dashboard.setGridEnabled(checked)

    def addItemMenu(self):
        menu = QtW.QMenu()
        menu.addAction("Add Text", lambda: self.dashboard.addItem(TextItem))
        menu.addAction("Add Button", lambda: self.dashboard.addItem(ButtonItem))
        return menu


class Dashboard(QtW.QWidget):
    def __init__(self):
        super(Dashboard, self).__init__()
        self.setLayout(Layout())
        self.editMode = False
        self.gridEnabled = False
        self.gridSize = 10
        self.mouseDragsWidget = None
        self.mouseDragOffset = None
        self.setMouseTracking(True)

    def addItem(self, cls):
        item = cls(self)
        item.setEnabled(not self.editMode)
        self.layout().addWidget(item)
        self.startItemDrag(item)
        self.mouseDragOffset = QtC.QPoint(0, 0)

    def setGridEnabled(self, enabled: bool):
        self.gridEnabled = enabled
        self.repaint()

    def startItemDrag(self, item: QtW.QWidget):
        self.mouseDragsWidget = item
        self.mouseDragsWidget.setAttribute(QtC.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def endItemDrag(self):
        self.mouseDragsWidget.setAttribute(QtC.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.mouseDragsWidget = None
        self.mouseDragOffset = None

    def isItemDragging(self):
        return self.mouseDragsWidget is not None

    def mouseMoveEvent(self, event: QtG.QMouseEvent) -> None:
        if self.mouseDragsWidget:
            size = self.mouseDragsWidget.size()
            pos = event.pos() - QtC.QPoint(size.width() // 2, size.height() // 2)
            if self.mouseDragOffset is None:
                self.mouseDragOffset = self.mouseDragsWidget.pos() - pos
            pos += self.mouseDragOffset
            if self.gridEnabled:
                pos = QtC.QPoint(
                    pos.x() // self.gridSize * self.gridSize,
                    pos.y() // self.gridSize * self.gridSize,
                )
            self.mouseDragsWidget.move(pos)

    def mousePressEvent(self, event: QtG.QMouseEvent) -> None:
        if event.button() == QtC.Qt.MouseButton.LeftButton:
            if self.isItemDragging():
                self.endItemDrag()
            elif self.editMode:
                for item in self.layout().children():
                    if item.mouseHovering:
                        self.startItemDrag(item)
                        break

    def mouseReleaseEvent(self, event: QtG.QMouseEvent) -> None:
        if event.button() == QtC.Qt.MouseButton.LeftButton:
            if self.isItemDragging():
                self.endItemDrag()

    def paintEvent(self, event: QtG.QPaintEvent):
        super().paintEvent(event)
        if self.gridEnabled and self.editMode:
            painter = QtG.QPainter(self)
            painter.setPen(QtG.QPen(QtG.QColor(127, 127, 127, 100), 0.5, QtC.Qt.PenStyle.SolidLine))
            for x in range(0, self.width(), self.gridSize):
                painter.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), self.gridSize):
                painter.drawLine(0, y, self.width(), y)


class Layout(QtW.QLayout):
    def __init__(self):
        super(Layout, self).__init__()
        self.itemsList = []

    def addItem(self, item: QtW.QLayoutItem):
        self.itemsList.append(item)

    def removeItem(self, item: QtW.QLayoutItem):
        self.itemsList.remove(item)
        return super().removeItem(item)

    def children(self):
        return [item.widget() for item in self.itemsList]

    def count(self) -> int:
        return len(self.itemsList)

    def itemAt(self, index) -> QtW.QWidget:
        if index < len(self.itemsList):
            return self.itemsList[index]
        return None

    def takeAt(self, index) -> QtW.QWidget:
        if index < len(self.itemsList):
            item = self.itemsList[index]
            self.removeItem(item)
            return item
        return None

    def sizeHint(self) -> QtC.QSize:
        x = 0
        y = 0
        for item in self.children():
            x = max(x, item.x() + item.width())
            y = max(y, item.y() + item.height())
        return QtC.QSize(x, y)

    def minimumSize(self) -> QtC.QSize:
        x = 0
        y = 0
        for item in self.children():
            x = max(x, item.width())
            y = max(y, item.height())
        return QtC.QSize(x, y)


class Item(Design.HBox):
    def __init__(self, widget: QtW.QWidget, dashboard: Dashboard):
        self.widget = widget
        self.dashboard = dashboard
        super(Item, self).__init__(widget, spacing=0)
        self.mouseHovering = False

    def setEnabled(self, enabled: bool):
        # self.widget.setEnabled(enabled)
        self.widget.setAttribute(QtC.Qt.WidgetAttribute.WA_TransparentForMouseEvents, not enabled)
        self.repaint()

    def enterEvent(self, event: QtG.QEnterEvent) -> None:
        self.mouseHovering = True
        self.repaint()
        return super().enterEvent(event)

    def leaveEvent(self, event: QtG.QEnterEvent) -> None:
        self.mouseHovering = False
        self.repaint()
        return super().leaveEvent(event)

    def paintEvent(self, event: QtG.QPaintEvent) -> None:
        super().paintEvent(event)
        if self.dashboard.editMode:
            painter = QtG.QPainter(self)
            painter.setPen(QtG.QPen(QtG.QColor(255, 0, 0, 100), 3, QtC.Qt.PenStyle.SolidLine))
            if self.mouseHovering:
                painter.setBrush(QtG.QBrush(QtG.QColor(127, 127, 127, 255)))
            else:
                painter.setBrush(QtC.Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, self.width(), self.height())


class TextItem(Item):
    def __init__(self, dashboard: Dashboard):
        super(TextItem, self).__init__(Design.Label("text"), dashboard)
        self.setFixedSize(80, 30)


class ButtonItem(Item):
    def __init__(self, dashboard: Dashboard):
        super(ButtonItem, self).__init__(Design.Button("button", flat=False, size="medium"), dashboard)
        self.setFixedSize(80, 30)
