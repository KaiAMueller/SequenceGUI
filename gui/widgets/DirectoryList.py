import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.widgets.Design as Design

INDENTATION_WIDTH = 12


class DirectoryList(QtW.QWidget):
    def __init__(self, dock, itemKind):
        super(DirectoryList, self).__init__()
        self.dock = dock
        self.itemKind = itemKind
        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.items = {}
        self.listVBox = Design.VBox(spacing=0)

        self.currentSelection = None
        self.onSelectionChanged = None
        self.onItemRightPressed = None
        self.onItemGotMoved = None

        self.scrollArea = QtW.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(Design.VBox(self.listVBox, EntryTail(self)))
        self.scrollArea.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.layout().addWidget(self.scrollArea)

    def add(self, path, icon, isDir):
        self.items[path] = Entry(self, path, icon, isDir)
        self.listVBox.layout().addWidget(self.items[path])

    def remove(self, path):
        self.listVBox.layout().removeWidget(self.items[path])
        self.items[path].setParent(None)
        self.items[path].deleteLater()
        self.items.pop(path)

    def itemGotMoved(self, oldPath, newPath):
        if self.onItemGotMoved is not None:
            self.onItemGotMoved(oldPath, newPath)

    def moveItem(self, oldPath, newPath):
        self.updateItemPath(oldPath, newPath)
        self.sortItems()

    def setItemInfo(self, path, info):
        if path in self.items:
            self.items[path].setInfo(info)

    def updateItemPath(self, oldPath, newPath):
        self.items[newPath] = self.items.pop(oldPath)
        self.items[newPath].path = newPath
        self.items[newPath].updateLabel()
        self.items[newPath].updateLeftSideSpacer()
        self.items[newPath].updateVisibility()

    def sortItems(self):
        try:
            for item in self.items.values():
                item.updateSortingKey()
        except Exception:
            return
        sortedItems = sorted(self.items.items(), key=lambda x: x[1].sortingKey)
        for i, (path, item) in enumerate(sortedItems):
            self.listVBox.layout().removeWidget(item)
            self.listVBox.layout().insertWidget(i, item)

    def visiblityToAllDirsClosed(self):
        for path, item in self.items.items():
            if path.find("/") == -1:
                item.setVisible(True)
            else:
                item.setVisible(False)

    def setCurrentSelection(self, path, silent=False):
        if self.currentSelection == path:
            return
        self.currentSelection = path
        self.repaint()
        if not silent and self.onSelectionChanged is not None:
            self.onSelectionChanged(path)

    def checkIfDirEmpty(self, path):
        for item in self.items.values():
            if item.path.find(path + "/") == 0:
                return False
        return True


class EntryTail(Design.Frame):
    def __init__(self, dirList: DirectoryList):
        super(EntryTail, self).__init__(Design.VBox(Design.Spacer(), Design.HBox(Design.Spacer(), spacing=0), spacing=0))
        self.dirList = dirList
        self.setMinimumHeight(20)
        self.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QtG.QDragEnterEvent):
        if not e.mimeData().hasFormat(self.dirList.dock.itemKind):
            return
        e.accept()

    def dragLeaveEvent(self, e: QtG.QDragLeaveEvent):
        pass

    def dropEvent(self, e: QtG.QDropEvent):
        for item in self.dirList.items.values():
            item.updateDragHovered(False)
        if not e.mimeData().hasFormat(self.dirList.dock.itemKind):
            return
        dragItemPath = e.mimeData().data(self.dirList.dock.itemKind).data().decode("utf-8")
        dragItem = self.dirList.items[dragItemPath]
        dragItemName = dragItemPath.split("/")[-1]
        if dragItemName in self.dirList.items:
            if self.dirList.items[dragItemName] != dragItem:
                Design.errorDialog("Error", dragItemName + " already exists")
            return
        self.dirList.itemGotMoved(dragItemPath, dragItemName)
        e.accept()

    def mousePressEvent(self, e: QtG.QMouseEvent):
        self.dirList.setCurrentSelection(None)

    def contextMenuEvent(self, e: QtG.QContextMenuEvent):
        self.dirList.dock.openAddItemMenu(e.globalPos())


class Entry(Design.Frame):
    def __init__(self, dirList: DirectoryList, path: str, icon: str, isDir: bool):
        self.leftSideSpacer = QtW.QLabel("")
        self.iconLabel = Design.Label(icon)
        self.textLabel = Design.Label(path.split("/")[-1])
        self.infoLabel = Design.Label(" ")
        super(Entry, self).__init__(
            Design.HBox(
                self.leftSideSpacer,
                self.iconLabel,
                self.textLabel,
                Design.Spacer(),
                self.infoLabel,
                spacing=0,
            )
        )
        self.dirList = dirList
        self.path = path
        self.icon = icon
        self.isDir = isDir
        self.sortingKey = path.lower()
        self.setObjectName("dirListEntry")
        self.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)
        self.dragStartPos = None
        self.isDragHovered = False
        self.updateLeftSideSpacer()

    def updateLabel(self):
        self.textLabel.setText(self.path.split("/")[-1])

    def setIcon(self, icon):
        self.icon = icon
        self.iconLabel.setText(icon)

    def setInfo(self, info):
        self.infoLabel.setText(info)

    def contextMenuEvent(self, e: QtG.QContextMenuEvent):
        self.dirList.onItemRightPressed(self.path, e.globalPos())

    def mousePressEvent(self, e: QtG.QMouseEvent):
        if e.button() == QtC.Qt.MouseButton.LeftButton:
            self.dragStartPos = e.pos()
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtG.QMouseEvent):
        if self.dragStartPos is not None and (e.pos() - self.dragStartPos).manhattanLength() > 10:
            self.drawStartPos = None
            drag = QtG.QDrag(self)
            mimeData = QtC.QMimeData()
            mimeData.setData(self.dirList.dock.itemKind, self.path.encode("utf-8"))
            drag.setMimeData(mimeData)
            pixmap = QtG.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec(supportedActions=QtC.Qt.DropAction.CopyAction | QtC.Qt.DropAction.MoveAction)
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtG.QMouseEvent):
        if self.dragStartPos is not None and (e.pos() - self.dragStartPos).manhattanLength() <= 10:
            if self.isDir:
                self.expandButtonClicked()
            else:
                if self.dirList.currentSelection == self.path:
                    self.dirList.setCurrentSelection(None)
                else:
                    self.dirList.setCurrentSelection(self.path)
            self.dragStartPos = None

    def dragEnterEvent(self, e: QtG.QDragEnterEvent):
        if not e.mimeData().hasFormat(self.dirList.dock.itemKind):
            return
        if self.isDir:
            dir = self.path
        else:
            dir = self.getAboveDirPath()
        if dir in self.dirList.items:
            self.dirList.items[dir].updateDragHovered(True)
        e.accept()

    def dragMoveEvent(self, e: QtG.QDragMoveEvent):
        y = self.pos().y() + e.position().y() - self.dirList.scrollArea.verticalScrollBar().value()
        if y < self.dirList.scrollArea.height() / 3:
            self.dirList.scrollArea.verticalScrollBar().setValue(self.dirList.scrollArea.verticalScrollBar().value() - 2)
        elif y > 2 * self.dirList.scrollArea.height() / 3:
            self.dirList.scrollArea.verticalScrollBar().setValue(self.dirList.scrollArea.verticalScrollBar().value() + 2)
        return super().dragMoveEvent(e)

    def dragLeaveEvent(self, e: QtG.QDragLeaveEvent):
        for item in self.dirList.items.values():
            item.updateDragHovered(False)

    def updateDragHovered(self, isDragHovered):
        if isDragHovered == self.isDragHovered:
            return
        self.isDragHovered = isDragHovered
        self.repaint()

    def dropEvent(self, e: QtG.QDropEvent):
        for item in self.dirList.items.values():
            item.updateDragHovered(False)
        if not e.mimeData().hasFormat(self.dirList.dock.itemKind):
            return
        dragItemPath = e.mimeData().data(self.dirList.dock.itemKind).data().decode("utf-8")
        dragItem = self.dirList.items[dragItemPath]
        dropPath = self.path if self.isDir else self.getAboveDirPath()
        if dropPath.find(dragItemPath) == 0:
            return
        dragItemName = dragItemPath.split("/")[-1]
        newDragItemPath = dropPath + "/" + dragItemName if dropPath != "" else dragItemName
        if newDragItemPath in self.dirList.items:
            if self.dirList.items[newDragItemPath] != dragItem:
                Design.errorDialog("Error", dragItemName + " already exists in " + dropPath)
            return
        self.dirList.itemGotMoved(dragItemPath, newDragItemPath)
        e.accept()

    def updateLeftSideSpacer(self):
        self.leftSideSpacer.setFixedWidth(INDENTATION_WIDTH * (1 + self.path.count("/")))

    def updateSortingKey(self):
        tokens = self.path.split("/")
        newTokens = []
        for i in range(len(tokens)):
            dir = "/".join(tokens[: i + 1])
            if self.dirList.items[dir].isDir:
                newTokens.append("0" + tokens[i].lower())
            else:
                newTokens.append("1" + tokens[i].lower())
        self.sortingKey = "/".join(newTokens)

    def getAboveDirPath(self):
        return "/".join(self.path.split("/")[:-1])

    def paintEvent(self, e: QtG.QPaintEvent):
        painter = QtG.QPainter(self)
        intendation_count = self.path.count("/")
        if self.path == self.dirList.currentSelection:
            painter.setPen(QtC.Qt.PenStyle.NoPen)
            painter.setBrush(QtG.QBrush(QtG.QColor(128, 128, 200, 100)))
            painter.drawRect(0, 0, self.width(), self.height())
        elif self.isDragHovered:
            painter.setPen(QtC.Qt.PenStyle.NoPen)
            painter.setBrush(QtG.QBrush(QtG.QColor(128, 128, 128, 150)))
            painter.drawRect(0, 0, self.width(), self.height())
        for i in range(intendation_count):
            painter.setPen(QtG.QPen(QtG.QColor(128, 128, 128, 255), 1.5))
            x = INDENTATION_WIDTH * (2 + i)
            painter.drawLine(x, 0, x, self.height())
        if self.icon == "📂":
            painter.setPen(QtG.QPen(QtG.QColor(128, 128, 128, 255), 1))
            x = INDENTATION_WIDTH * (2 + intendation_count)
            painter.drawLine(x - 5, self.height() - 5, x, self.height())
            painter.drawLine(x + 5, self.height() - 5, x, self.height())
        painter.end()
        return super().paintEvent(e)

    def updateVisibility(self):
        tokens = self.path.split("/")
        for i in range(1, len(tokens)):
            dir = "/".join(tokens[:i])
            if dir == "":
                continue
            if self.dirList.items[dir].icon == "📁":
                self.setVisible(False)
                return
        if not self.isVisible():
            self.setVisible(True)

    def expandButtonClicked(self):
        if self.icon == "📁":
            self.setIcon("📂")
            for path, item in self.dirList.items.items():
                if path.find(self.path + "/") == 0:
                    item.updateVisibility()
        elif self.icon == "📂":
            self.setIcon("📁")
            for path, item in self.dirList.items.items():
                if path.find(self.path + "/") == 0:
                    item.updateVisibility()
