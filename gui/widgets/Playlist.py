import asyncio

import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.artiq_master_manager
import gui.widgets.Design as Design
import gui.widgets.Dock
import gui.widgets.SequenceEditor as SequenceEditor
import gui.crate.FileManager as FileManager

import datetime

STATUS_COLORS = {
    "pending": QtG.QColor(255, 255, 0, 50),
    "preparing": QtG.QColor(255, 255, 0, 50),
    "prepare_done": QtG.QColor(127, 255, 0, 50),
    "sending": QtG.QColor(0, 150, 150, 50),
    "running": QtG.QColor(0, 0, 255, 50),
    "done": QtG.QColor(0, 255, 0, 50),
    "error": QtG.QColor(255, 0, 0, 50),
}

dock = None


def sequenceCompiled(codeID, seqName, variables):
    dock.runObserver.addRunInfo(str(codeID), seqName, variables)
    
    
def sequenceStarted(codeID):
    dock.dataReader.updateStatusByCodeID(str(codeID), "running")
    dock.runObserver.currentRun = str(codeID)


def sequenceFinished(codeID):
    dock.dataReader.updateStatusByCodeID(str(codeID), "done")
    dock.runObserver.removeRunInfo(str(codeID))


def deleteRID(rid=None):
    if rid is None:
        rid = dock.dataReader.currentlyRunningRID
        if rid is None:
            return -1
    if rid not in dock.dataReader.treeItems:
        return -1
    if dock.dataReader.treeItems[rid].status != "done":
        asyncio.ensure_future(gui.artiq_master_manager.rpcClient.delete(int(rid)))


class Dock(gui.widgets.Dock.Dock):
    def __init__(self, gui):
        super(Dock, self).__init__("🤘 Playlist", gui)
        global dock
        dock = self

        self.runObserver = RunObserver()

        self.tree = Tree()
        self.dataReader = DataReader(self.tree)
        self.setWidget(self.tree)

        self.clearButton = Design.Button("🧹", size="medium")
        self.clearButtonMenu = QtW.QMenu()
        self.clearButton.setMenu(self.clearButtonMenu)
        self.clearButtonMenu.addAction("Clear all", lambda: self.dataReader.clearList(all=True))
        self.clearButtonMenu.addAction("Clear only done", lambda: self.dataReader.clearList())

        self.setRightWidget(self.clearButton)


class RunObserver:
    def __init__(self):
        self.runs = {}
        self.currentRun = None

    def addRunInfo(self, codeID, seqName, variables):
        self.runs[codeID] = {
            "seqName": seqName,
            "variables": variables,
        }

    def getRunInfo(self, codeID):
        return self.runs[codeID]

        
    def getCurrentRunInfo(self):
        if self.currentRun in self.runs:
            return self.runs[self.currentRun]
        return None

    def removeRunInfo(self, codeID):
        if codeID in self.runs:
            del self.runs[codeID]
        if codeID == self.currentRun:
            self.currentRun = None


class TreeItem(QtW.QTreeWidgetItem):
    def __init__(self, seqName: str, status: str, rid: str, codeID: str, duration: str, previousRID):
        super(TreeItem, self).__init__([seqName, status, rid, duration])
        self.seqName = seqName
        self.status = status
        self.duration = duration
        self.rid = rid
        self.codeID = codeID
        self.previousRID = previousRID
        self.finishedDate = None
        self.updateStatus(status)

    def updateStatus(self, status: str):
        self.status = status
        self.setText(1, status)
        if status in STATUS_COLORS:
            color = STATUS_COLORS[status]
        else:
            color = QtG.QColor(0, 0, 0, 0)
        # set row background
        self.setBackground(1, color)
        if status == "done":
            self.finishedDate = datetime.datetime.now()
        if status == "error":
            self.finishedDate = datetime.datetime.now()
        for key, value in dock.dataReader.codeIDdict.items():
            value.updateTime()
        self.updateTime()

    def updateTime(self):
        self.setText(3, self.getDueDate().strftime("%H:%M:%S"))
    
    def getDueDate(self):
        if self.finishedDate is not None:
            return self.finishedDate
        if self.previousRID is None:
            return datetime.datetime.now() + datetime.timedelta(seconds=float(self.duration) + 1) #+1 as a scheduling overhead estimation
        if self.previousRID not in dock.dataReader.treeItems:
            return datetime.datetime.now() + datetime.timedelta(seconds=float(self.duration) + 1)
        return dock.dataReader.treeItems[self.previousRID].getDueDate() + datetime.timedelta(seconds=float(self.duration) + 1)


class Tree(QtW.QTreeWidget):
    def __init__(self):
        super(Tree, self).__init__()
        self.setColumnCount(2)
        self.setHeaderLabels(["Sequence", "Status", "RID", "Expected end time"])
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            return
        menu = QtW.QMenu()
        menu.addAction("Delete", lambda: self.deleteActionClicked(item.rid))
        menu.exec(QtG.QCursor.pos())

    def deleteActionClicked(self, rid):
        deleteRID(rid)
        dock.dataReader.deleteItem(rid)


class DataReader:
    def __init__(self, tree: Tree):
        self.tree = tree
        self.treeItems = {}
        self.codeIDdict = {}
        self.currentlyRunningRID = None
        self.lastRID = None

    def read(self, updateData):
        # log(updateData)
        action = updateData["action"]
        if action == "setitem":
            self.setitem(updateData["path"], updateData["key"], updateData["value"])
        elif action == "delitem":
            pass

    def setitem(self, path: list, key: str, value: str):
        if path == []:
            codeID = str(value["expid"]["arguments"]["codeID"])
            seqName = dock.runObserver.runs[codeID]["seqName"]
            self.newItem(
                str(key),
                seqName,
                value["status"],
                codeID,
                str(value["expid"]["duration"]),
            )
        else:
            rid = str(path[0])
            if rid in self.treeItems:
                if key == "status":
                    if self.treeItems[rid].status != "done":
                        if value == "running":
                            value = "sending"
                        if value == "deleting":
                            value = "error"
                            SequenceEditor.sequenceFinished(self.treeItems[rid].seqName)
                        self.treeItems[rid].updateStatus(value)

    def newItem(self, rid, seqName, status, codeID, duration):
        self.treeItems[rid] = TreeItem(seqName, status, rid, codeID, duration, self.lastRID)
        self.lastRID = rid
        self.codeIDdict[codeID] = self.treeItems[rid]
        self.tree.addTopLevelItem(self.treeItems[rid])
        self.tree.scrollToBottom()
        FileManager.saveSequenceData(seqName, dock.dataReader.codeIDdict[codeID].rid)

    def deleteItem(self, rid):
        if rid in self.treeItems:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(self.treeItems[rid]))
            # self.tree.removeItemWidget(self.treeItems[rid])
            del self.codeIDdict[self.treeItems[rid].codeID]
            del self.treeItems[rid]

    def updateStatusByCodeID(self, codeID, status):
        if codeID in self.codeIDdict:
            if status == "running":
                self.currentlyRunningRID = self.codeIDdict[codeID].rid
            elif status == "done":
                self.currentlyRunningRID = None
            self.codeIDdict[codeID].updateStatus(status)

    def clearList(self, all=False):
        for rid in list(self.treeItems.keys()):
            if self.treeItems[rid].status == "done" or all:
                deleteRID(rid)
                self.deleteItem(rid)
