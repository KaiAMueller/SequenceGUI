import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW


class HorVBox(QtW.QWidget):
    def __init__(self, *widgets, spacing=None, margins=None):
        super(HorVBox, self).__init__()
        if spacing is None:
            spacing = 3
        if margins is None:
            margins = (0, 0, 0, 0)
        self.setLayout(self.genLayout())
        self.layout().setContentsMargins(*margins)
        self.layout().setSpacing(spacing)
        stretch = 0
        # if len(widgets) > 0 and type(widgets[0]) == list:
        #     widgets = widgets[0]
        for widget in widgets:
            if widget is None:
                continue
            if type(widget) is int:
                stretch = widget
            else:
                if type(widget) is str:
                    widget = QtW.QLabel(widget)
                self.layout().addWidget(widget, 1 if type(widget) is Spacer else stretch)
                stretch = 0

    def genLayout(self):
        return None


class HBox(HorVBox):
    def __init__(self, *widgets, **kwargs):
        super(HBox, self).__init__(*widgets, **kwargs)

    def genLayout(self):
        return QtW.QHBoxLayout()


class VBox(HorVBox):
    def __init__(self, *widgets, **kwargs):
        super(VBox, self).__init__(*widgets, **kwargs)

    def genLayout(self):
        return QtW.QVBoxLayout()


class ValueFont(QtG.QFont):
    def __init__(self):
        super(ValueFont, self).__init__("Consolas", 10)


class SmallValueFont(QtG.QFont):
    def __init__(self):
        super(SmallValueFont, self).__init__("Consolas", 8)


class SuperSmallValueFont(QtG.QFont):
    def __init__(self):
        super(SuperSmallValueFont, self).__init__("Consolas", 6)


class LabelFont(QtG.QFont):
    def __init__(self):
        super(LabelFont, self).__init__("Arial", 10)


class SmallLabelFont(QtG.QFont):
    def __init__(self):
        super(SmallLabelFont, self).__init__("Arial", 8)


class Grid(QtW.QWidget):
    def __init__(self, widgetss: list, spacing=None, margins=None, alignment=None):
        super(Grid, self).__init__()
        if spacing is None:
            spacing = 3
        if margins is None:
            margins = (0, 0, 0, 0)
        self.setLayout(QtW.QGridLayout())
        self.layout().setContentsMargins(*margins)
        self.layout().setSpacing(spacing)
        for i, widgets in enumerate(widgetss):
            for j, widget in enumerate(widgets):
                if widget is None:
                    continue
                if type(widget) is str:
                    widget = QtW.QLabel(widget)
                if alignment == QtC.Qt.AlignmentFlag.AlignLeft:
                    widget = HBox(widget, Spacer())
                elif alignment == QtC.Qt.AlignmentFlag.AlignRight:
                    widget = HBox(Spacer(), widget)
                self.layout().addWidget(widget, i, j)


class Spacer(QtW.QWidget):
    def __init__(self, x=None, y=None):
        super(Spacer, self).__init__()
        if x is not None and y is not None:
            self.setFixedSize(x, y)
        elif x is not None:
            self.setFixedWidth(x)
        elif y is not None:
            self.setFixedHeight(y)


class Frame(QtW.QFrame):
    def __init__(self, widget=None, margins=(0, 0, 0, 0)):
        super(Frame, self).__init__()
        self.setLayout(QtW.QVBoxLayout())
        self.setFrameStyle(QtW.QFrame.Shape.StyledPanel)
        self.layout().setContentsMargins(*margins)
        if widget is not None:
            self.layout().addWidget(widget)


class HLine(QtW.QFrame):
    def __init__(self):
        super(HLine, self).__init__()
        self.setFrameShape(QtW.QFrame.Shape.StyledPanel)
        self.setFixedHeight(1)


class VLine(QtW.QFrame):
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QtW.QFrame.Shape.StyledPanel)
        self.setFixedWidth(1)


class Splitter(QtW.QSplitter):
    def __init__(self, widgets, sizes=None, orientation=QtC.Qt.Orientation.Horizontal):
        super(Splitter, self).__init__(orientation)
        self.setHandleWidth(2)
        for widget in widgets:
            self.addWidget(widget)
        if sizes is not None:
            for i in range(len(sizes)):
                sizes[i] = int(sizes[i] * 1920)
            self.setSizes(sizes)


class TabWidget(QtW.QTabWidget):
    def __init__(self, *widgets):
        super(TabWidget, self).__init__()
        self.setTabPosition(QtW.QTabWidget.TabPosition.North)
        self.setDocumentMode(True)
        for widget in widgets:
            self.addTab(*widget)


class Label(QtW.QLabel):
    def __init__(self, text, alignment=QtC.Qt.AlignmentFlag.AlignLeft):
        super(Label, self).__init__(text)
        self.setAlignment(alignment)
        self.setWordWrap(True)
        self.set(text)

    def get(self):
        return self.text()

    def set(self, value):
        self.setText(value)
        if value == "":
            self.setMaximumHeight(0)
        else:
            self.setMaximumHeight(1000)


class HintText(Label):
    def __init__(self, text, alignment=QtC.Qt.AlignmentFlag.AlignLeft):
        super(HintText, self).__init__(text, alignment)
        self.setObjectName("HintText")
        font = QtG.QFont()
        font.setPointSize(8)
        self.setFont(font)


class Button(QtW.QPushButton):
    def __init__(self, text, flat=True, size="small"):
        super(Button, self).__init__(text)
        self.setObjectName(size)
        self.setFlat(flat)
        self.setFocusPolicy(QtC.Qt.FocusPolicy.NoFocus)
        self.onRightClick = None

    def mousePressEvent(self, event):
        if event.button() == QtC.Qt.MouseButton.RightButton and self.onRightClick is not None:
            self.onRightClick()
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        event.accept()


class IconButton(Button):
    def __init__(self, icon, callback):
        super(IconButton, self).__init__(icon)
        self.setFont(QtG.QFont("Consolas", 14))
        self.setObjectName("noPaddingButton")
        self.clicked.connect(callback)


class LabelButton(Label):
    def __init__(self, text, alignment=QtC.Qt.AlignmentFlag.AlignLeft):
        super(LabelButton, self).__init__(text, alignment)
        self.setObjectName("LabelButton")
        self.onClicked = None
        self.enabled = True

    def setEnabled(self, enabled):
        self.enabled = enabled

    def mousePressEvent(self, event):
        if event.button() == QtC.Qt.MouseButton.LeftButton and self.enabled:
            if self.onClicked is not None:
                self.onClicked()
            event.accept()
        else:
            super().mousePressEvent(event)


class ComboBoxWithOnClickCall(QtW.QComboBox):
    def __init__(self, fun):
        super(ComboBoxWithOnClickCall, self).__init__()
        self.fun = fun

    def showPopup(self):
        if self.fun is not None:
            self.fun()
        return super().showPopup()


class DragableWindowDesign:
    def __init__(self):
        super(DragableWindowDesign, self).__init__()
        self.dragPos = None

    # make window draggable
    def mousePressEvent(self, event):
        if event.button() == QtC.Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtC.Qt.MouseButton.LeftButton:
            self.dragPos = None
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragPos is None:
            return
        self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos)
        self.dragPos = event.globalPosition().toPoint()
        event.accept()


class CloseButton(QtW.QPushButton):
    def __init__(self, parent=None, red=True):
        super(CloseButton, self).__init__(" 🞪 ", parent)
        if red:
            self.setObjectName("RedCloseButton")
        else:
            self.setObjectName("CloseButton")
        font = QtG.QFont()
        font.setPointSize(15)
        self.setFont(font)
        self.setFlat(True)
        self.setToolTip("Close")
        self.setFocusPolicy(QtC.Qt.FocusPolicy.NoFocus)


class DeleteButton(QtW.QPushButton):
    def __init__(self, tooltip="Delete"):
        super(DeleteButton, self).__init__(" 🗑 ")
        self.setObjectName("RedDeleteButton")
        font = QtG.QFont()
        font.setPointSize(15)
        self.setFont(font)
        self.setFlat(True)
        self.setToolTip(tooltip)
        self.setFocusPolicy(QtC.Qt.FocusPolicy.NoFocus)


class RunButton(QtW.QPushButton):
    def __init__(self, parent=None):
        super(RunButton, self).__init__(" ⯈ ", parent)
        self.setObjectName("RunButton")
        font = QtG.QFont()
        font.setPointSize(15)
        self.setFont(font)
        self.setFlat(True)


class DialogDesign(DragableWindowDesign, QtW.QDialog):
    def __init__(self, title="", leftCornerLabel="", closeButtonEnabled=True):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
        self.setLayout(QtW.QVBoxLayout())
        super().layout().setContentsMargins(0, 0, 0, 0)
        super().layout().setSpacing(0)
        self.frame = QtW.QFrame()
        # soft border
        self.frame.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.frameLayout = QtW.QVBoxLayout()
        self.frameLayout.setContentsMargins(0, 0, 0, 0)
        self.frameLayout.setSpacing(0)
        self.frame.setLayout(self.frameLayout)

        self.closeButton = None
        if closeButtonEnabled:
            self.closeButton = CloseButton()
            self.closeButton.clicked.connect(self.close)
        super().layout().addWidget(
            Frame(
                VBox(
                    HBox(
                        QtW.QLabel(leftCornerLabel),
                        Spacer(),
                        QtW.QLabel(title),
                        Spacer(),
                        self.closeButton,
                        5,
                    ),
                    1,
                    self.frame,
                    spacing=3,
                )
            )
        )

    def layout(self):
        return self.frameLayout


class ProgressDialog(DialogDesign):
    def __init__(self, title="", leftCornerLabel=""):
        super(ProgressDialog, self).__init__(title, leftCornerLabel)
        self.progressBar = QtW.QProgressBar()
        self.progressRange = 300
        self.progressBar.setRange(0, self.progressRange)
        self.progressBar.setValue(0)
        self.frameLayout.addWidget(self.progressBar)
        self.onClose = None
        self.setFixedWidth(self.progressRange)
        self.setFixedHeight(100)

    def setProgress(self, progress):
        self.progressBar.setValue(int(progress * self.progressRange))

    def closeEvent(self, event):
        if self.onClose is not None:
            self.onClose()
        return super().closeEvent(event)


class AlignedButton(QtW.QPushButton):
    def __init__(self, text, alignment=QtC.Qt.AlignmentFlag.AlignLeft):
        super(AlignedButton, self).__init__(text)
        if alignment == QtC.Qt.AlignmentFlag.AlignLeft:
            self.setObjectName("leftAlignedButton")
        elif alignment == QtC.Qt.AlignmentFlag.AlignRight:
            self.setObjectName("rightAlignedButton")


class PassiveButton(QtW.QPushButton):
    def __init__(self, text):
        super(PassiveButton, self).__init__(text)
        self.setObjectName("PassiveButton")
        self.setFlat(True)
        self.setCheckable(True)

    def mousePressEvent(self, event):
        return event.ignore()

    def mouseReleaseEvent(self, event):
        return event.ignore()


class DragableItemList(QtW.QWidget):
    def __init__(self, orientation=QtC.Qt.Orientation.Vertical):
        super(DragableItemList, self).__init__()
        self.orientation = orientation
        self.itemSelectedOnClickAutomatically = False
        self.onIndexingChanged = None
        self.itemsDragable = True
        self.dragItem = None
        self.dragStartMousePos = None
        self.dragStartItemPos = None
        self.dragStartIndex = None
        self.dragMoved = False
        self.dragLastSnapPos = None

        self.onSelectionChanged = None
        self.currentSelection = None
        self.onItemRightPressed = None
        self.onItemNoDragReleased = None
        self.items = {}

        self.scrollArea = QtW.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.listWidget = QtW.QWidget()
        self.listLayout = QtW.QVBoxLayout() if self.orientation == QtC.Qt.Orientation.Vertical else QtW.QHBoxLayout()

        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setWidget(self.listWidget)
        self.listWidget.setLayout(self.listLayout)

        self.layout().addWidget(self.scrollArea)

        self.listLayout.setContentsMargins(0, 0, 0, 0)
        self.listLayout.setSpacing(0)
        self.listLayout.setAlignment(QtC.Qt.AlignmentFlag.AlignTop | QtC.Qt.AlignmentFlag.AlignLeft)

        self.alignment = QtC.Qt.AlignmentFlag.AlignLeft

    def add(self, item, index=None):
        item.mousePressEvent = lambda e: self.onButtonMousePressEvent(e, item)
        item.mouseMoveEvent = lambda e: self.onButtonMouseMoveEvent(e, item)
        item.mouseReleaseEvent = lambda e: self.onButtonMouseReleaseEvent(e, item)
        if index is not None:
            self.listLayout.insertWidget(index, item)
        else:
            self.listLayout.addWidget(item)

    def remove(self, item):
        self.listLayout.removeWidget(item)

    def indexOf(self, item):
        return self.listLayout.indexOf(item)

    def count(self):
        return self.listLayout.count()

    def renameItem(self, oldName, newName):
        if oldName == newName:
            return
        assert oldName in self.items
        assert newName not in self.items
        self.items[newName] = self.items[oldName]
        del self.items[oldName]
        if self.currentSelection == oldName:
            self.currentSelection = newName

    def getItemList(self):
        return [item for item in (self.listLayout.itemAt(i).widget() for i in range(self.listLayout.count()))]

    def onButtonMousePressEvent(self, event, item):
        if event.button() == QtC.Qt.MouseButton.RightButton:
            if self.onItemRightPressed is not None:
                self.onItemRightPressed(event, item)
        if event.button() == QtC.Qt.MouseButton.LeftButton and self.itemsDragable:
            item.raise_()
            self.dragItem = item
            self.dragMoved = False
            self.dragStartMousePos = event.globalPosition()
            self.dragStartItemPos = item.pos()
            self.dragLastSnapPos = item.pos()
            self.dragStartIndex = self.listLayout.indexOf(item)
        if self.itemSelectedOnClickAutomatically:
            return super(type(item), item).mousePressEvent(event)

    def onButtonMouseMoveEvent(self, event, item):
        if self.dragItem is not None:
            self.dragMoved = True
            moveChange = (event.globalPosition() - self.dragStartMousePos).toPoint()
            moveChange = QtC.QPoint(moveChange.x(), 0) if self.orientation == QtC.Qt.Orientation.Horizontal else QtC.QPoint(0, moveChange.y())
            self.dragItem.move(self.dragStartItemPos + moveChange)
            self.snapItems()
        return super(type(item), item).mouseMoveEvent(event)

    def onButtonMouseReleaseEvent(self, event, item):
        accepted = False
        if self.dragItem is not None:
            if self.dragMoved:
                accepted = True
                self.snapItems()
                self.listLayout.insertWidget(self.listLayout.indexOf(self.dragItem), self.dragItem)
                newIndex = self.listLayout.indexOf(self.dragItem)
                if self.dragStartIndex != newIndex:
                    if self.onIndexingChanged is not None:
                        self.onIndexingChanged(self.dragItem.text(), self.dragStartIndex, newIndex)
            self.dragItem = None
            self.dragMoved = False
            self.dragStartMousePos = None
            self.dragStartItemPos = None
            self.dragLastSnapPos = None
            self.dragStartIndex = None
        if not accepted and self.onItemNoDragReleased is not None:
            self.onItemNoDragReleased(event, item)
        return super(type(item), item).mouseReleaseEvent(event)

    def snapItems(self):
        if self.dragItem is not None:
            index = self.listLayout.indexOf(self.dragItem)
            if self.orientation == QtC.Qt.Orientation.Vertical:
                pos = self.dragItem.pos().y()
                pos += self.dragItem.height() / 2 if self.dragItem.pos().y() > self.dragLastSnapPos.y() else -self.dragItem.height() / 2
            else:
                pos = self.dragItem.pos().x()
                pos += self.dragItem.width() / 2 if self.dragItem.pos().x() > self.dragLastSnapPos.x() else -self.dragItem.width() / 2
            for item in (self.listLayout.itemAt(i).widget() for i in range(self.listLayout.count())):
                if item == self.dragItem:
                    continue
                otherPos = item.pos().y() if self.orientation == QtC.Qt.Orientation.Vertical else item.pos().x()
                otherIndex = self.listLayout.indexOf(item)
                if (pos < otherPos) ^ (index < otherIndex):
                    self.dragLastSnapPos = item.pos()
                    if index < otherIndex:
                        self.listLayout.insertWidget(index, item)
                    else:
                        self.listLayout.insertWidget(otherIndex, self.dragItem)
                    break

    def changeIndex(self, name, newIndex):
        if name not in self.items:
            return
        self.listLayout.insertWidget(newIndex, self.items[name])

    def mousePressEvent(self, event):
        if event.button() == QtC.Qt.MouseButton.LeftButton:
            for name in self.items:
                self.setItemSelected(name, False)
            if self.currentSelection is not None:
                oldSelection = self.currentSelection
                self.currentSelection = None
                if self.onSelectionChanged is not None:
                    self.onSelectionChanged(oldSelection, None)
        return super().mousePressEvent(event)

    def setCurrentSelection(self, name, silent=False):
        if name == self.currentSelection:
            return
        if name not in self.items:
            name = None
        if self.currentSelection is not None:
            self.setItemSelected(self.currentSelection, False)
        if name is not None:
            self.setItemSelected(name, True)
        oldSelection = self.currentSelection
        self.currentSelection = name
        if self.onSelectionChanged is not None and not silent:
            self.onSelectionChanged(oldSelection, name)

    def onItemClicked(self, item):
        for n in self.items:
            if n != item.name:
                self.setItemSelected(n, False)
        selected = self.isItemSelected(item.name)
        if not self.itemSelectedOnClickAutomatically:
            selected = not selected
            self.setItemSelected(item.name, selected)
        oldSelection = self.currentSelection
        self.currentSelection = item.name if selected else None
        if self.onSelectionChanged is not None:
            self.onSelectionChanged(oldSelection, item.name if selected else None)

    def setItemSelected(self, name, selected):
        pass

    def isItemSelected(self, name):
        return False


class SelectableButtonList(DragableItemList):
    def __init__(self):
        super(SelectableButtonList, self).__init__()
        self.itemSelectedOnClickAutomatically = True

    def add(self, name):
        button = AlignedButton(name, self.alignment)
        button.setFont(SmallLabelFont())
        button.name = name
        button.setFlat(True)
        button.setCheckable(True)
        button.setSizePolicy(QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda: self.onItemClicked(button))
        self.items[name] = button
        super(SelectableButtonList, self).add(button)

    def remove(self, name):
        if name == self.currentSelection:
            self.currentSelection = None
        if name in self.items:
            super(SelectableButtonList, self).remove(self.items[name])
            self.items[name].deleteLater()
            del self.items[name]

    def renameItem(self, oldName, newName):
        super(SelectableButtonList, self).renameItem(oldName, newName)
        self.items[newName].setText(newName)
        self.items[newName].name = newName

    def setItemSelected(self, name, selected):
        if name in self.items:
            self.items[name].setChecked(selected)

    def isItemSelected(self, name):
        return name in self.items and self.items[name].isChecked()


class Menu(QtW.QMenu):
    def __init__(self, actions):
        super(Menu, self).__init__()
        self.actions = actions
        for action in self.actions:
            self.addAction(action)


class Action(QtG.QAction):
    def __init__(self, title, callback):
        super(Action, self).__init__(title)
        self.triggered.connect(callback)


class CheckableAction(QtG.QAction):
    def __init__(self, text, callback, default=False):
        super(CheckableAction, self).__init__(text)
        self.setCheckable(True)
        self.setChecked(default)
        self.triggered.connect(callback)

    def set(self, value):
        self.setChecked(value)

    def get(self):
        return self.isChecked()


class MenuSelectFromDirList(QtW.QMenu):
    def __init__(self, data: dict, callback, removedOptions=[], title="Select"):
        super(MenuSelectFromDirList, self).__init__(title)
        self.data = data
        self.callback = callback
        self.removedOptions = removedOptions
        self.subMenus = []
        self.addEntries(self, "")

    def addEntries(self, menu: QtW.QMenu, path: str):
        for key, value in self.data.items():
            if key in self.removedOptions:
                continue
            if key.startswith(path):
                if value["isDir"]:
                    subMenu = QtW.QMenu(key[len(path) :])
                    self.subMenus.append(subMenu)
                    self.addEntries(subMenu, key + "/")
                    menu.addMenu(subMenu)
                else:
                    if key[len(path) :].count("/") == 0:
                        menu.addAction(key[len(path) :], lambda key=key: self.callback(key))
        if menu.isEmpty():
            menu.addAction("Empty").setEnabled(False)


def confirmationDialog(title, text):
    dialog = DialogDesign(title, "⚠️")
    dialog.frameLayout.addWidget(QtW.QLabel(text))
    returnValue = []

    def closeDialog(value):
        returnValue.append(value)
        dialog.close()

    yesButton = Button("Yes")
    yesButton.clicked.connect(lambda: closeDialog(True))
    noButton = Button("No")
    noButton.clicked.connect(lambda: closeDialog(False))
    dialog.frameLayout.addWidget(HBox(yesButton, noButton, 5))
    yesButton.setFocus()
    dialog.exec()
    return returnValue[0] if len(returnValue) > 0 else False


def infoDialog(title, text):
    dialog = DialogDesign(title, "ℹ️")
    dialog.frameLayout.addWidget(QtW.QLabel(text))
    okButton = Button("Ok")
    okButton.clicked.connect(dialog.close)
    dialog.frameLayout.addWidget(okButton)
    dialog.exec()


def errorDialog(title, text):
    dialog = DialogDesign(title, "❌")
    dialog.frameLayout.addWidget(QtW.QLabel(text))
    okButton = Button("Ok")
    okButton.clicked.connect(dialog.close)
    dialog.frameLayout.addWidget(okButton)
    dialog.exec()


def inputDialog(title, text, defaultText=""):
    dialog = DialogDesign(title, "❓")
    dialog.frameLayout.addWidget(QtW.QLabel(text))
    inputField = QtW.QLineEdit(defaultText)
    dialog.frameLayout.addWidget(inputField)
    okButton = Button("Ok")
    returnValue = []

    def confirm():
        returnValue.append(inputField.text())
        dialog.close()

    okButton.clicked.connect(confirm)
    inputField.returnPressed.connect(confirm)
    dialog.frameLayout.addWidget(okButton)
    inputField.setFocus()
    dialog.exec()
    return returnValue[0] if len(returnValue) > 0 else None


def comboBoxDialog(title, text, options, defaultOption=None, allowNone=False):
    dialog = DialogDesign(title, "❓")
    dialog.frameLayout.addWidget(QtW.QLabel(text))
    comboBox = QtW.QComboBox()
    if allowNone:
        comboBox.addItem("")
    comboBox.addItems(options)
    if defaultOption is not None:
        comboBox.setCurrentText(defaultOption)
    dialog.frameLayout.addWidget(comboBox)
    okButton = Button("Ok")
    returnValue = []

    def confirm():
        returnValue.append(comboBox.currentText())
        dialog.close()

    okButton.clicked.connect(confirm)
    dialog.frameLayout.addWidget(okButton)
    comboBox.setFocus()
    dialog.exec()
    return returnValue[0] if len(returnValue) > 0 else None
