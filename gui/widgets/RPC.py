import copy
import multiprocessing
import os
import queue
import threading
import traceback

import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW
import watchdog.events
import watchdog.observers

import gui.compiler
import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Dock as Dock
import gui.widgets.Input as Input
import gui.widgets.Playlist as Playlist
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.Variables as Variables
import gui.widgets.Viewer as Viewer
from gui.widgets.Log import log

dock = None
title = "🌍 RPC"
itemKind = "RPC"
device_name = "sequence_gui_rpc"

# keys in each sub-rpc-entry: "script", "activeThreadOrProcess", "activeThreadOrProcessExitFlag"
managers = {}


def argReader(s):
    if '"' in s or "'" in s:
        raise Exception("No \" or ' allowed in args")
    return s


def executeScript(script, args, kargs, rpcName, runVariables=None, codeID=None, exitFlag=None, logQueue=None):
    try:
        gdict = {
            "print": (log if logQueue is None else lambda *logArgs: logQueue.put(logArgs)),
            "args": args,
            "kargs": kargs,
            "exitFlag": exitFlag,
            "runVariables": runVariables,
            "codeID": codeID,
        }
        exec(script, gdict)
    except Exception as e:
        if logQueue is None:
            log(e)
        else:
            logQueue.put((e, traceback.format_exc()))
    if logQueue is None:
        dock.setActiveThreadOrProcess(rpcName, None)
    else:
        logQueue.put(None)


def queueReader(logQueue, rpcName):
    while True:
        try:
            logArgs = logQueue.get()
            if logArgs is None:
                break
            else:
                log(*logArgs)
        except queue.Empty:
            break
    dock.setActiveThreadOrProcess(rpcName, None)


def isRPCActive(rpcName):
    return managers[rpcName]["activeThreadOrProcess"] is not None


class Server:
    def print(self, *args):
        print(*args)

    def run(self, *args, **kargs):
        if "codeID" in kargs:
            codeID = kargs["codeID"]
        else:  
            codeID = None
        try:
            rpcName = args[0]
            args = [str(arg) for arg in args[1:]]
            currentRun = Playlist.dock.runObserver.getCurrentRunInfo()
            if currentRun is not None:
                runVariables = currentRun["variables"]
                if codeID is None:
                    codeID = currentRun["codeID"]
            else:
                runVariables = copy.deepcopy(crate.variables)
                if codeID is None:
                    codeID = "manual"
            script = crate.RPC.getScript(rpcName)
            mode = crate.RPC.getValue(rpcName, "mode")
            if managers[rpcName]["activeThreadOrProcess"] is not None:
                raise Exception(f'RPC "{rpcName}" is already running')
            if mode == "thread":
                exitFlag = threading.Event()
                thread = threading.Thread(
                    target=executeScript,
                    args=(script, args, kargs, rpcName, runVariables, codeID, exitFlag),
                )
                dock.setActiveThreadOrProcess(rpcName, thread, exitFlag)
                thread.start()
            elif mode == "subprocess":
                logQueue = multiprocessing.Queue()
                exitFlag = multiprocessing.Event()
                process = multiprocessing.Process(
                    target=executeScript,
                    args=(
                        script,
                        args,
                        kargs,
                        rpcName,
                        runVariables,
                        codeID,
                        exitFlag,
                        logQueue,
                    ),
                )
                dock.setActiveThreadOrProcess(rpcName, process, exitFlag)
                process.start()
                # start logQueue reader
                queueReaderThread = threading.Thread(target=queueReader, args=(logQueue, rpcName))
                queueReaderThread.start()
            elif mode == "normal":
                exitFlag = threading.Event()
                dock.setActiveThreadOrProcess(rpcName, "normal", exitFlag)
                executeScript(script, args, kargs, rpcName, runVariables, codeID, exitFlag)
        except Exception as e:
            log(e)

    def startSequence(self, seqName):
        log(f"Sequence {seqName} got started remotely")
        try:
            gui.compiler.compileAndRun(seqName)
        except Exception as e:
            log(e)

    def setVariable(self, name, value):
        try:
            crate.Variables.ValueChange(name, "value", value)
        except Exception as e:
            log(e)

    def sequenceStarted(self, codeID, seqName):
        Playlist.sequenceStarted(codeID)
        SequenceEditor.sequenceStarted(seqName)

    def sequenceFinished(self, codeID, seqName):
        SequenceEditor.sequenceFinished(seqName)
        Playlist.sequenceFinished(codeID)


class WatchdogEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, eventQueue):
        super(WatchdogEventHandler, self).__init__()
        self.eventQueue = eventQueue

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            file = event.src_path.split("/")[-1]
            self.eventQueue.put(file)


class Dock(Dock.ListConfigDockExtension):
    def __init__(self, gui):
        super(Dock, self).__init__(
            title=title,
            gui=gui,
            widgetClass=Widget,
            itemKind=itemKind,
            backendCallbacks=crate.RPC,
            icon="🌍",
        )
        global dock
        dock = self

        self.eventQueue = queue.Queue()
        self.watchdogEventHandler = WatchdogEventHandler(self.eventQueue)
        self.watchdogObserver = watchdog.observers.Observer()
        path = crate.FileManager.getScriptsPath()
        self.watchdogObserver.schedule(self.watchdogEventHandler, path=path)
        try:
            self.watchdogObserver.start()
        except Exception:
            QtW.QMessageBox.critical(None, "Error", "Error while starting watchdog observer. Usually restarting the software fixes this.")
            raise Exception("Error while starting watchdog observer")
        QtC.QTimer.singleShot(100, self.checkEventQueue)

    def stopWatchdogObserver(self):
        self.watchdogObserver.stop()
        self.watchdogObserver.join()

    def checkEventQueue(self):
        QtC.QTimer.singleShot(100, self.checkEventQueue)
        changedFiles = set()
        while not self.eventQueue.empty():
            changedFiles.add(self.eventQueue.get())
        for changedFile in changedFiles:
            self.onExternalScriptFileChange(changedFile)

    def loadCrate(self):
        super(Dock, self).loadCrate(crate.rpcs)

    def onExternalScriptFileChange(self, file):
        # find rpcName
        for rpcName, rpcData in crate.rpcs.items():
            if rpcData["file"] == file:
                oldScript = managers[rpcName]["script"]
                newScript = crate.RPC.getScript(rpcName)
                crate.RPC.ScriptChange(rpcName, oldScript, newScript)
                break

    def addItem(self, name, **kwargs):
        managers[name] = {
            "script": crate.RPC.getScript(name),
            "activeThreadOrProcess": None,
            "activeThreadOrProcessExitFlag": None,
        }
        super(Dock, self).addItem(name, **kwargs)

    def deleteItem(self, name):
        super(Dock, self).deleteItem(name)
        del managers[name]

    def renameItem(self, oldName, newName):
        super(Dock, self).renameItem(oldName, newName)
        managers[newName] = managers[oldName]
        del managers[oldName]

    def widgetValueChange(self, name, valueName, value):
        super(Dock, self).widgetValueChange(name, valueName, value)
        if valueName == "script":
            managers[name]["script"] = value

    def killProcess(self, rpcName=None):
        if rpcName is None:
            if self.configWidget is None:
                return
            rpcName = self.configWidget.name
        if managers[rpcName]["activeThreadOrProcess"] is not None:
            managers[rpcName]["activeThreadOrProcess"].terminate()
            self.setActiveThreadOrProcess(None)

    def setExitFlag(self, rpcName=None):
        if rpcName is None:
            if self.configWidget is None:
                return
            rpcName = self.configWidget.name
        if managers[rpcName]["activeThreadOrProcessExitFlag"] is not None:
            managers[rpcName]["activeThreadOrProcessExitFlag"].set()

    def setActiveThreadOrProcess(self, rpcName, thread=None, exitFlag=None):
        managers[rpcName]["activeThreadOrProcess"] = thread
        managers[rpcName]["activeThreadOrProcessExitFlag"] = exitFlag
        self.list.setItemInfo(rpcName, "" if thread is None else "🔴")
        if self.configWidget is not None and rpcName == self.configWidget.name:
            self.configWidget.updateStateButtonText()


class Widget(Design.VBox):
    def __init__(self, name, dock):
        self.name = name
        self.dock = dock

        self.stateButton = Design.Button("")
        self.updateStateButtonText()
        self.stateButton.clicked.connect(self.stateButtonClicked)

        self.openInVsCodeButton = Design.Button("Open in VS Code")
        self.openInVsCodeButton.clicked.connect(self.openInVsCode)

        self.valueFields = {
            "script": Input.CodeEditor(
                default=crate.RPC.getScript(self.name),
                changedCallback=lambda value: crate.RPC.ScriptChange(self.name, None, value),
            ),
            "mode": Input.ComboBox(
                itemsGenerateFunction=lambda: ["normal", "thread", "subprocess"],
                default=crate.RPC.getValue(self.name, "mode"),
                changedCallback=lambda value: crate.RPC.ValueChange(self.name, "mode", value),
            ),
        }
        super(Widget, self).__init__(
            Design.HBox(
                self.openInVsCodeButton,
                "Execution Mode:",
                self.valueFields["mode"],
                self.stateButton,
                Design.Spacer(),
                Viewer.InfoButton(crate.rpcs[self.name]),
            ),
            self.valueFields["script"],
        )

    def updateStateButtonText(self):
        if managers[self.name]["activeThreadOrProcess"] is None:
            self.stateButton.setText("Not Running")
        else:
            self.stateButton.setText(f"Running {'Process' if type(managers[self.name]['activeThreadOrProcess']) is multiprocessing.Process else 'Thread'} 🔴")

    def openInVsCode(self):
        try:
            path = crate.FileManager.getScriptsPath() + crate.RPC.getValue(self.name, "file")
            os.system(f"code {path}")
        except Exception:
            Design.errorDialog("Error", "Error while opening VS Code\n" + traceback.format_exc())

    def valueChange(self, valueName, value):
        self.valueFields[valueName].set(value)

    def stateButtonClicked(self):
        menu = QtW.QMenu()
        if managers[self.name]["activeThreadOrProcess"] is None:
            menu.addAction("Run Manually", self.runManuallyActionClicked)
        else:
            menu.addAction("set exitFlag", self.dock.setExitFlag)
            if type(managers[self.name]["activeThreadOrProcess"]) is multiprocessing.Process:
                menu.addAction("Kill Process", self.dock.killProcess)
        menu.exec(self.stateButton.mapToGlobal(QtC.QPoint(0, self.stateButton.height())))

    def runManuallyActionClicked(self):
        try:
            text = Design.inputDialog("Enter Arguments", f"Enter Arguments for {self.name}.", "")
            if text is None:
                return
            tokens = argReader(text).strip().split(" ")
            args = []
            for arg in tokens:
                if arg == "":
                    continue
                args.append(Variables.replacer(arg))
            Server.run(Server(), self.name, *args)
        except Exception as e:
            log(e)


class SegmentWidget(Design.HBox):
    def __init__(self, segment, name):
        self.segment = segment
        self.name = name
        self.configDialog = None
        self.configWidgets = {
            "args": Input.TextField(
                default=crate.Sequences.getRPCValue(self.segment.sequence.name, self.segment.name, self.name, "args"),
                changedCallback=lambda value: crate.Sequences.RPCValueChange(
                    self.segment.sequence.name,
                    self.segment.name,
                    self.name,
                    "args",
                    value,
                ),
                reader=argReader,
                replacer=Variables.replacer,
                dontUpdateMetrics=False,
                alignment=QtC.Qt.AlignmentFlag.AlignLeft,
            ),
            "kargs": Input.KeyValueEditor(
                default=crate.Sequences.getRPCValue(self.segment.sequence.name, self.segment.name, self.name, "kargs"),
                changedCallback=lambda value: crate.Sequences.RPCValueChange(
                    self.segment.sequence.name,
                    self.segment.name,
                    self.name,
                    "kargs",
                    value,
                ),
                valueReplacer=Variables.replacer,
            ),
        }
        self.textLabel = QtW.QLabel(name)
        self.textLabel.setFont(Design.SmallLabelFont())
        self.previewWidget = QtW.QPushButton()
        self.previewWidget.setFont(Design.SmallValueFont())
        self.updatePreviewWidget()
        self.previewWidget.clicked.connect(self.openConfig)
        super(SegmentWidget, self).__init__(self.textLabel, Design.Spacer(), self.previewWidget)

    def updatePreviewWidget(self):
        args = crate.Sequences.getRPCValue(self.segment.sequence.name, self.segment.name, self.name, "args")
        kargs = crate.Sequences.getRPCValue(self.segment.sequence.name, self.segment.name, self.name, "kargs")
        text = f"({args}, {kargs})" if kargs != {} else f"{args}"
        self.previewWidget.setText(text if text != "" else "No Args")

    def openConfig(self):
        if self.configDialog is None:
            self.configDialog = ConfigDialog(self)
            self.configDialog.exec()

    def closeConfig(self):
        if self.configDialog is not None:
            for configWidget in self.configWidgets.values():
                configWidget.setParent(self)
            self.configDialog.close()
            self.configDialog = None

    def getHeightBlocks(self):
        return 1

    def valueChange(self, valueName, value):
        self.configWidgets[valueName].set(value)
        self.updatePreviewWidget()


class ConfigDialog(Design.DialogDesign):
    def __init__(self, portStateWidget):
        title = f"{portStateWidget.name} Config"
        super(ConfigDialog, self).__init__(title, "⚙", closeButtonEnabled=False)
        self.portStateWidget = portStateWidget
        self.name = portStateWidget.name
        self.segment = portStateWidget.segment
        self.configWidgets = portStateWidget.configWidgets

        # event filter for undo/redo shortcuts
        self.installEventFilter(self)

        # window title
        self.setWindowTitle(title)

        # delete button
        self.deleteButton = Design.DeleteButton("Delete RPC")
        self.deleteButton.clicked.connect(self.deleteButtonClicked)

        # save button
        self.doneButton = Design.Button(" Done ")
        self.doneButton.clicked.connect(self.doneButtonClicked)

        # layout
        self.layout().addWidget(
            Design.VBox(
                Design.HBox("args", self.configWidgets["args"]),
                "kargs",
                Design.HBox(self.configWidgets["kargs"]),
                Design.Spacer(),
                Design.HBox(
                    Design.Spacer(),
                    Viewer.InfoButton(crate.sequences[self.segment.sequence.name]["segments"][self.segment.name]["rpcs"][self.name]),
                ),
                Design.HBox(1, self.doneButton, self.deleteButton),
            )
        )

        self.doneButton.setFocus()

    # # event filter for undo/redo shortcuts
    def eventFilter(self, obj: QtC.QObject, e: QtC.QEvent) -> bool:
        if obj == self:
            if e.type() == QtC.QEvent.Type.KeyPress:
                if e.key() == QtC.Qt.Key.Key_Z and e.modifiers() == QtC.Qt.KeyboardModifier.ControlModifier:
                    crate.undo()
                    return True
                elif e.key() == QtC.Qt.Key.Key_Y and e.modifiers() == QtC.Qt.KeyboardModifier.ControlModifier:
                    crate.redo()
                    return True
        return super().eventFilter(obj, e)

    def deleteButtonClicked(self):
        self.portStateWidget.closeConfig()
        crate.Sequences.RPCDelete(self.segment.sequence.name, self.segment.name, self.name)

    def doneButtonClicked(self):
        for configWidget in self.configWidgets.values():
            if hasattr(configWidget, "onEditingFinished"):
                # trigger editingFinished signal manually because
                # otherwise it triggers only after the config closes
                # which calls then updatevisibility after its closed
                # which makes it appear somewhere else (visual bug)
                configWidget.onEditingFinished()
        self.portStateWidget.closeConfig()
