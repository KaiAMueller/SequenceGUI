import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW

import gui.artiq_master_manager as artiq_master_manager
import gui.compiler
import gui.crate as crate
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Dock
import gui.widgets.Playlist as Playlist
import gui.widgets.Segment as Segment
import gui.widgets.Sequence as Sequence
import gui.widgets.TableSequenceView as TableSequenceView
import gui.widgets.Viewer as Viewer
from gui.widgets.Log import log
import gui.widgets.Input as Input

dock = None
title = "⏳ Sequence Editor"
align_ports = "Align ports"
show_full_portnames = "Show full portnames"
rearrangable_portstates = "Rearrangable portstates"
enable_big_run_button = "Enable big run button"


def sequenceStarted(seqName):
    dock.list.setItemInfo(seqName, "🔴")
    dock.currentlyRunningSequence = seqName
    dock.currentlyRunningSequenceButton.setText(f"🔴 {seqName}")
    dock.currentlyRunningSequenceButton.setHidden(False)
    if dock.configWidget is not None:
        if type(dock.configWidget) is Sequence.Widget:
            dock.configWidget.setIsCurrentlyRunning(True)



def sequenceFinished(seqName=None):
    if seqName is None:
        seqName = dock.currentlyRunningSequence
        if seqName is None:
            return
    dock.list.setItemInfo(seqName, "")
    dock.currentlyRunningSequence = None
    dock.currentlyRunningSequenceButton.setHidden(True)
    if dock.currentlyRunningSequenceMenu is not None:
        dock.currentlyRunningSequenceMenu.close()
    if dock.configWidget is not None:
        if type(dock.configWidget) is Sequence.Widget:
            dock.configWidget.setIsCurrentlyRunning(False)


class Dock(gui.widgets.Dock.ListConfigDockExtension):
    def __init__(self, gui):
        super(Dock, self).__init__(
            title=title,
            gui=gui,
            itemKind="Sequence",
            widgetClass=Sequence.Widget,
            backendCallbacks=crate.Sequences,
            icon="⏳",
        )
        global dock
        dock = self
        TableSequenceView.setSequenceEditorDock(self)

        self.addSettingsAction(
            align_ports,
            lambda checked: crate.Config.ValueChange(title, align_ports, checked),
            crate.Config.getDockConfig(title, align_ports),
        )
        self.addSettingsAction(
            show_full_portnames,
            lambda checked: crate.Config.ValueChange(title, show_full_portnames, checked),
            crate.Config.getDockConfig(title, show_full_portnames),
        )
        self.addSettingsAction(
            rearrangable_portstates,
            lambda checked: crate.Config.ValueChange(title, rearrangable_portstates, checked),
            crate.Config.getDockConfig(title, rearrangable_portstates),
        )
        self.addSettingsAction(
            enable_big_run_button,
            lambda checked: crate.Config.ValueChange(title, enable_big_run_button, checked),
            crate.Config.getDockConfig(title, enable_big_run_button),
        )

        self.runButton = Design.RunButton()
        self.runButton.clicked.connect(self.runCurrentSequence)
        self.runButton.setToolTip("Compile and run selected sequence")
        self.runButton.setEnabled(False)

        self.showCompiledCodeButton = Design.IconButton("🗔", self.showCompiledCode)
        self.showCompiledCodeButton.setToolTip("Compile and show code")
        self.showCompiledCodeButton.setEnabled(False)

        self.currentlyRunningSequence = None
        self.currentlyRunningSequenceButton = Design.Button(" ", size="medium")
        self.currentlyRunningSequenceButton.clicked.connect(self.currentlyRunningSequenceClicked)
        self.currentlyRunningSequenceButton.setToolTip("Currently running sequence")
        self.currentlyRunningSequenceButton.setHidden(True)
        self.currentlyRunningSequenceMenu = None

        self.setRightWidget(Design.HBox(self.showCompiledCodeButton, self.runButton))
        self.setLeftWidget(Design.HBox(self.currentlyRunningSequenceButton))

    def loadCrate(self):
        # fix subsequence references
        
        for seqName, seqData in crate.sequences.items():
            seqData["appearances"] = {}
        for seqName, seqData in crate.sequences.items():
            for segName, segData in seqData["segments"].items():
                if segData["type"] == "subsequence":
                    if seqName not in crate.sequences[segData["subsequence"]]["appearances"]:
                        crate.sequences[segData["subsequence"]]["appearances"][seqName] = [segName]
                    else:
                        crate.sequences[segData["subsequence"]]["appearances"][seqName].append(segName)

        super(Dock, self).loadCrate(crate.sequences)

    def currentlyRunningSequenceClicked(self):
        self.currentlyRunningSequenceMenu = QtW.QMenu()
        self.currentlyRunningSequenceMenu.addAction("Cancel", self.cancelCurrentlyRunningSequenceClicked)
        self.currentlyRunningSequenceMenu.exec(self.currentlyRunningSequenceButton.mapToGlobal(QtC.QPoint(0, self.currentlyRunningSequenceButton.height())))

    def cancelCurrentlyRunningSequenceClicked(self):
        result = Playlist.deleteRID()
        if result == -1:
            sequenceFinished()

    def renameItem(self, oldName, newName):
        super(Dock, self).renameItem(oldName, newName)
        # check all occurences of subsequences in other sequences
        if dock.configWidget is not None:
            if type(dock.configWidget) is Sequence.Widget:
                for segment in dock.configWidget.segments():
                    if type(segment) is Segment.Subsequence and segment.configWidgets["subsequence"].get() == oldName:
                        segment.configWidgets["subsequence"].updateItems(oldName, newName)

    def extraContextMenuActions(self, seqName):
        pre_compile_rpc = crate.Sequences.getSequenceValue(seqName, "pre_compile_rpc")
        return [
            Design.Action("Duplicate", lambda: self.duplicateActionClicked(seqName)),
            Design.Action(
                f"Pre-Compile Script: {pre_compile_rpc}",
                lambda: self.preCompileScriptActionClicked(seqName),
            ),
        ]

    def duplicateActionClicked(self, seqName):
        if seqName not in crate.sequences:
            return
        newName = util.textToIdentifier(
            Design.inputDialog(
                "Duplicate sequence",
                "Enter a name for the duplicated sequence",
                seqName,
            )
        )
        if newName is None or newName == "":
            return
        if newName in self.list.items:
            Design.errorDialog("Error", f'Sequence "{newName}" already exists.')
            return
        crate.Sequences.Add(newName, crate.sequences[seqName])

    def preCompileScriptActionClicked(self, seqName):
        selection = Design.comboBoxDialog(
            title="Pre-Compile Script",
            text="Select a script to run before compiling the sequence",
            options=list(crate.rpcs.keys()),
            defaultOption=crate.Sequences.getSequenceValue(seqName, "pre_compile_rpc"),
            allowNone=True,
        )
        if selection == "":
            selection = None
        crate.Sequences.ValueChange(seqName, "pre_compile_rpc", selection)
        argsText = Design.inputDialog(
            "Pre-Compile Script Arguments",
            "Enter arguments for the pre-compile script",
            crate.Sequences.getSequenceValue(seqName, "pre_compile_args"),
        )
        if argsText is None:
            argsText = ""
        crate.Sequences.ValueChange(seqName, "pre_compile_args", argsText)

    def changeSelection(self, newSelection):
        isValidSelection = newSelection is not None and not crate.sequences[newSelection]["isDir"]
        self.runButton.setEnabled(isValidSelection)
        self.showCompiledCodeButton.setEnabled(isValidSelection)
        super().changeSelection(newSelection)
        if isValidSelection:
            self.configWidget.alignPorts()
            self.configWidget.alignDescriptions()
        TableSequenceView.updateTable()

    def runCurrentSequence(self):
        if artiq_master_manager.test_mode:
            Design.errorDialog("Error", "Test device_db is active. Cannot run on Hardware.")
            return
        gui.compiler.compileAndRun(self.list.currentSelection)

    def showCompiledCode(self):
        try:
            compiledCode, codeID, duration = gui.compiler.compileCode(self.list.currentSelection)
        except Exception as e:
            log(e)
            return
        Viewer.Dialog(compiledCode).exec()

    def configChange(self, option, value):
        super().configChange(option, value)
        if option == align_ports:
            self.configWidget.alignPorts(value)
            self.configWidget.alignDescriptions(value)
        elif option == show_full_portnames:
            self.configWidget.updateShowFullPortnames(value)
        elif option == enable_big_run_button:
            if self.configWidget is not None:
                self.configWidget.updateReallyBigRunStopButtons(value)
                