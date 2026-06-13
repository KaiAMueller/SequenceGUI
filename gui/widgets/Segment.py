# native python imports
import copy

import PySide6.QtCore as QtC
import PySide6.QtGui as QtG

# third party imports
import PySide6.QtWidgets as QtW

# local imports
import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.PortState.CurrentDriver as CurrentDriver
import gui.widgets.PortState.Fastino as Fastino
import gui.widgets.PortState.Mirny as Mirny
import gui.widgets.PortState.Sampler as Sampler
import gui.widgets.PortState.TTL as TTL
import gui.widgets.PortState.Urukul as Urukul
import gui.widgets.PortState.Zotino as Zotino
import gui.widgets.RPC
import gui.widgets.LabSetup
import gui.widgets.Sequence as Sequence
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.TableSequenceView as TableSequenceView
import gui.widgets.Variables as Variables
import gui.widgets.Viewer as Viewer

DEFAULT_SEG_WIDTH = 150
HEIGHT_BLOCK = 25


class Widget(Design.Frame):
    def __init__(self, sequence: Sequence, name):
        super(Widget, self).__init__()
        self.sequence = sequence
        self.name = name
        self.setObjectName("segment")
        self.configWidgets = {}
        self.contentWidget = Design.VBox()

        self.jsonButton = Viewer.InfoButton(crate.sequences[self.sequence.name]["segments"][self.name])

        self.configWidgets["enabled"] = Input.ToggleButton(
            default=crate.Sequences.segmentGet(self.sequence.name, self.name, "enabled"),
            changedCallback=lambda value: crate.Sequences.SegmentValueChange(self.sequence.name, self.name, "enabled", value),
        )

        self.configWidgets["duration"] = Input.UnitValueField(
            default=crate.Sequences.segmentGet(self.sequence.name, self.name, "duration"),
            allowedUnits=[
                {"text": "s", "factor": 1},
                {"text": "ms", "factor": 1e-3},
                {"text": "us", "factor": 1e-6},
                {"text": "ns", "factor": 1e-9},
            ],
            reader=float,
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.SegmentValueChange(self.sequence.name, self.name, "duration", value),
            dontUpdateMetrics=False,
            alignment=QtC.Qt.AlignmentFlag.AlignRight,
        )

        self.configWidgets["description"] = Design.HintText(crate.Sequences.segmentGet(self.sequence.name, self.name, "description"))

        self.setFixedWidth(DEFAULT_SEG_WIDTH)

        self.layout().addWidget(
            Design.VBox(
                Design.HBox(
                    self.configWidgets["enabled"],
                    Design.Spacer(),
                    self.configWidgets["duration"],
                ),
                self.configWidgets["description"],
                Design.HLine(),
                self.contentWidget,
            )
        )
        self.updateWidgetsEnabled()

    def updateWidgetsEnabled(self, enabled=None):
        if enabled is None:
            enabled = crate.Sequences.segmentGet(self.sequence.name, self.name, "enabled")
        for w in self.findChildren(QtW.QWidget):
            toEnabledClasses = [
                QtW.QLineEdit,
                QtW.QComboBox,
                QtW.QCheckBox,
                QtW.QPushButton,
            ]
            if any([isinstance(w, c) for c in toEnabledClasses]):
                if w != self.configWidgets["enabled"]:
                    w.setEnabled(enabled)

    def contextMenuEvent(self, e):
        menu = QtW.QMenu()
        menu.addAction("Edit Description").triggered.connect(self.editDescription)
        menu.addSeparator()
        index = self.sequence.segmentList.indexOf(self)
        createNewLeftMenu = QtW.QMenu("Create New Left")
        createNewLeftMenu.addAction("PortState Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData={"type": "portstate"}, index=index))
        createNewLeftMenu.addAction("Subsequence Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData={"type": "subsequence"}, index=index))
        createNewLeftMenu.addAction("TriggerWait Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData={"type": "triggerwait"}, index=index))
        createNewRightMenu = QtW.QMenu("Create New Right")
        createNewRightMenu.addAction("PortState Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData={"type": "portstate"}, index=index + 1))
        createNewRightMenu.addAction("Subsequence Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData={"type": "subsequence"}, index=index + 1))
        createNewRightMenu.addAction("TriggerWait Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData={"type": "triggerwait"}, index=index + 1))
        menu.addMenu(createNewLeftMenu)
        menu.addMenu(createNewRightMenu)
        dataCopy = copy.deepcopy(crate.sequences[self.sequence.name]["segments"][self.name])
        menu.addAction("Duplicate Segment").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.sequence.name, segData=dataCopy, index=index + 1))
        menu.addAction("Delete Segment").triggered.connect(self.confirmDeleteSegment)
        menu.exec(self.mapToGlobal(e.pos()))

    def confirmDeleteSegment(self):
        if Design.confirmationDialog("Delete Segment?", "Delete Segment?"):
            crate.Sequences.SegmentDelete(self.sequence.name, self.name)

    def editDescription(self):
        description = crate.Sequences.segmentGet(self.sequence.name, self.name, "description")
        description = Design.inputDialog("Edit Description", "Edit Description", description)
        if description is not None:
            crate.Sequences.SegmentValueChange(self.sequence.name, self.name, "description", description)

    def segmentValueChange(self, valueName, newValue):
        self.configWidgets[valueName].set(newValue)
        if valueName == "enabled":
            self.updateWidgetsEnabled(newValue)
        if valueName == "description":
            self.sequence.alignDescriptions()
        TableSequenceView.updateTable()

    def compile(self, segStack):
        pass

    def text(self):
        return self.name
        
    


class PortStates(Widget):
    MODULE_TO_WIDGET_CLASS = {
        "artiq.coredevice.ttl": TTL.Widget,
        "artiq.coredevice.zotino": Zotino.Widget,
        "artiq.coredevice.fastino": Fastino.Widget,
        "artiq.coredevice.ad9910": Urukul.Widget,
        "artiq.coredevice.adf5356": Mirny.Widget,
        "artiq.coredevice.sampler": Sampler.Widget,
        "custom.CurrentDriver": CurrentDriver.Widget,
    }

    def __init__(self, sequence: Sequence, name):
        super(PortStates, self).__init__(sequence, name)
        self.rpcWidgets = {}
        self.portStateWidgets = {}
        self.rpcSpacers = {}
        self.portStateSpacers = {}
        self.rpcLayout = Design.VBox(spacing=0)
        self.portStateLayout = Design.VBox(spacing=0)
        self.setAcceptDrops(True)
        self.addEventButton = Design.Button("➕ Add Event ")
        self.addEventButton.clicked.connect(self.addEventButtonClicked)
        for portName in crate.labsetup.keys():
            self.addPortStateSpacer(portName)
            if portName in crate.sequences[sequence.name]["segments"][name]["ports"]:
                self.addPortState(portName)
        for rpcName in crate.rpcs.keys():
            self.addRPCSpacer(rpcName)
            if rpcName in crate.sequences[sequence.name]["segments"][name]["rpcs"]:
                self.addRPC(rpcName)
        self.contentWidget.layout().addWidget(
            Design.VBox(
                self.rpcLayout,
                self.portStateLayout,
                Design.HLine(),
                Design.Spacer(),
                Design.HBox(self.addEventButton, Design.Spacer(), self.jsonButton),
            )
        )

    def addEventButtonClicked(self):
        menu = QtW.QMenu()

        portMenu = Design.MenuSelectFromDirList(
            crate.labsetup,
            lambda portName: crate.Sequences.PortStateAdd(self.sequence.name, self.name, portName),
            removedOptions=list(self.portStateWidgets.keys()),
            title="Add Port",
        )

        rpcMenu = Design.MenuSelectFromDirList(
            crate.rpcs,
            lambda rpcName: crate.Sequences.RPCAdd(self.sequence.name, self.name, rpcName),
            removedOptions=list(self.rpcWidgets.keys()),
            title="Add RPC",
        )

        # portMenu = QtW.QMenu("Add Port")
        # rpcMenu = QtW.QMenu("Add RPC")
        menu.addMenu(portMenu)
        menu.addMenu(rpcMenu)
        # portOptions = [portName for portName in crate.labsetup if portName not in self.portStateWidgets and not crate.labsetup[portName]["isDir"]]
        # rpcOptions = [rpcName for rpcName in crate.rpcs if rpcName not in self.rpcWidgets and not crate.rpcs[rpcName]["isDir"]]
        # for portName in portOptions:
        #     portMenu.addAction(portName).triggered.connect(lambda: crate.Sequences.PortStateAdd(self.sequence.name, self.name, portName))
        # for rpcName in rpcOptions:
        #     rpcMenu.addAction(rpcName).triggered.connect(lambda: crate.Sequences.RPCAdd(self.sequence.name, self.name, rpcName))
        menu.exec(self.addEventButton.mapToGlobal(QtC.QPoint(0, self.addEventButton.height())))

    def addPortStateSpacer(self, portName):
        self.portStateSpacers[portName] = Design.Spacer()
        self.portStateSpacers[portName].setFixedHeight(0)
        # respect labsetup order
        index = list(crate.labsetup.keys()).index(portName)
        self.portStateLayout.layout().insertWidget(index, self.portStateSpacers[portName])

    def addPortState(self, portName, noAlign=False):
        self.portStateWidgets[portName] = PortStates.MODULE_TO_WIDGET_CLASS[crate.labsetup[portName]["module"]](self, portName)
        self.portStateLayout.layout().replaceWidget(self.portStateSpacers[portName], self.portStateWidgets[portName])
        self.portStateSpacers[portName].setFixedHeight(0)
        if not noAlign:
            self.sequence.alignPorts()
        TableSequenceView.updateTable()

    def deletePortState(self, portName):
        self.portStateLayout.layout().replaceWidget(self.portStateWidgets[portName], self.portStateSpacers[portName])
        self.portStateSpacers[portName].setFixedHeight(self.portStateWidgets[portName].height() if crate.Config.getDockConfig(SequenceEditor.title, SequenceEditor.align_ports) else 0)
        self.portStateWidgets[portName].deleteLater()
        self.portStateWidgets.pop(portName)
        self.sequence.alignPorts()
        TableSequenceView.updateTable()

    def renamePortState(self, oldPortName, newPortName):
        self.portStateSpacers[newPortName] = self.portStateSpacers.pop(oldPortName)
        if oldPortName in self.portStateWidgets:
            self.portStateWidgets[newPortName] = self.portStateWidgets.pop(oldPortName)
            self.portStateWidgets[newPortName].updateName(newPortName)
        TableSequenceView.updateTable()

    def sortPortStates(self):
        for portName in reversed(list(crate.labsetup.keys())):
            if portName in self.portStateWidgets:
                self.portStateLayout.layout().insertWidget(0, self.portStateWidgets[portName])
                self.portStateSpacers[portName].setFixedHeight(0)
            else:
                self.portStateLayout.layout().insertWidget(0, self.portStateSpacers[portName])

    def dealignPorts(self):
        for spacer in self.portStateSpacers.values():
            spacer.setFixedHeight(0)
        for spacer in self.rpcSpacers.values():
            spacer.setFixedHeight(0)

    def alignPorts(self, portHeightBlocks: dict, rpcHeightBlocks: dict):
        for portName, spacer in self.portStateSpacers.items():
            if portName in portHeightBlocks and portName not in self.portStateWidgets:
                spacer.setFixedHeight(int(portHeightBlocks[portName] * HEIGHT_BLOCK))
            else:
                spacer.setFixedHeight(0)
        for portName, widget in self.portStateWidgets.items():
            widget.setFixedHeight(int(portHeightBlocks[portName] * HEIGHT_BLOCK))

        for rpcName, spacer in self.rpcSpacers.items():
            if rpcName in rpcHeightBlocks and rpcName not in self.rpcWidgets:
                spacer.setFixedHeight(int(rpcHeightBlocks[rpcName] * HEIGHT_BLOCK))
            else:
                spacer.setFixedHeight(0)
        for rpcName, widget in self.rpcWidgets.items():
            widget.setFixedHeight(int(rpcHeightBlocks[rpcName] * HEIGHT_BLOCK))

    def getPortState(self, portName):
        return self.portStateWidgets[portName]

    def showFullPortnames(self, value):
        for portState in self.portStateWidgets.values():
            portState.showFullPortname(value)

    def addRPCSpacer(self, rpcName):
        self.rpcSpacers[rpcName] = Design.Spacer()
        self.rpcSpacers[rpcName].setFixedHeight(0)
        # respect order
        index = list(crate.rpcs.keys()).index(rpcName)
        self.rpcLayout.layout().insertWidget(index, self.rpcSpacers[rpcName])

    def addRPC(self, rpcName, noAlign=False):
        self.rpcWidgets[rpcName] = gui.widgets.RPC.SegmentWidget(self, rpcName)
        self.rpcLayout.layout().replaceWidget(self.rpcSpacers[rpcName], self.rpcWidgets[rpcName])
        self.rpcSpacers[rpcName].setFixedHeight(0)
        if not noAlign:
            self.sequence.alignPorts()
        TableSequenceView.updateTable()

    def deleteRPC(self, rpcName):
        self.rpcLayout.layout().replaceWidget(self.rpcWidgets[rpcName], self.rpcSpacers[rpcName])
        self.rpcSpacers[rpcName].setFixedHeight(self.rpcWidgets[rpcName].height() if crate.Config.getDockConfig(SequenceEditor.title, SequenceEditor.align_ports) else 0)
        self.rpcWidgets[rpcName].deleteLater()
        self.rpcWidgets.pop(rpcName)
        self.sequence.alignPorts()
        TableSequenceView.updateTable()

    def renameRPC(self, oldRpcName, newRpcName):
        self.rpcSpacers[newRpcName] = self.rpcSpacers.pop(oldRpcName)
        if oldRpcName in self.rpcWidgets:
            self.rpcWidgets[newRpcName] = self.rpcWidgets.pop(oldRpcName)
            self.rpcWidgets[newRpcName].name = newRpcName
            self.rpcWidgets[newRpcName].textLabel.setText(newRpcName)
        TableSequenceView.updateTable()

    def sortRPCs(self):
        for rpcName in reversed(list(crate.rpcs.keys())):
            if rpcName in self.rpcWidgets:
                self.rpcLayout.layout().insertWidget(0, self.rpcWidgets[rpcName])
                self.rpcSpacers[rpcName].setFixedHeight(0)
            else:
                self.rpcLayout.layout().insertWidget(0, self.rpcSpacers[rpcName])

    def getRPC(self, rpcName):
        return self.rpcWidgets[rpcName]

    def dragEnterEvent(self, e):
        widget = e.source()
        if widget.isDir:
            return
        if widget.path in self.portStateWidgets or widget.path in self.rpcWidgets:
            return
        if widget.path in crate.labsetup and widget.dirList.itemKind == gui.widgets.LabSetup.itemKind:
            e.accept()
        if widget.path in crate.rpcs and widget.dirList.itemKind == gui.widgets.RPC.itemKind:
            e.accept()

    def dropEvent(self, e):
        widget = e.source()
        if widget.isDir:
            return
        portName=widget.path
        if widget.path in crate.labsetup and widget.dirList.itemKind == gui.widgets.LabSetup.itemKind:
            crate.Sequences.PortStateAdd(self.sequence.name, self.name, portName)
            self.sortPortStates()
        elif widget.path in crate.rpcs and widget.dirList.itemKind == gui.widgets.RPC.itemKind:
            crate.Sequences.RPCAdd(self.sequence.name, self.name, portName)
            self.sortRPCs()
        self.sequence.alignPorts()
        TableSequenceView.updateTable()
        e.accept()
        


class Subsequence(Widget):
    def __init__(self, sequence: Sequence, name):
        super(Subsequence, self).__init__(sequence, name)
        self.configWidgets["subsequence"] = Input.BigComboBox(
            itemsGenerateFunction=lambda: list(crate.sequences.keys()),
            default=crate.Sequences.segmentGet(self.sequence.name, self.name, "subsequence"),
            changedCallback=lambda value: crate.Sequences.SegmentValueChange(self.sequence.name, self.name, "subsequence", value),
        )

        self.configWidgets["repeats"] = Input.TextField(
            default=crate.Sequences.segmentGet(self.sequence.name, self.name, "repeats"),
            reader=int,
            replacer=Variables.replacer,
            changedCallback=lambda value: crate.Sequences.SegmentValueChange(self.sequence.name, self.name, "repeats", value),
        )
        self.configWidgets["duration"].setReadOnly(True)

        self.contentWidget.layout().addWidget(
            Design.VBox(
                self.configWidgets["subsequence"],
                Design.HBox(
                    QtW.QLabel("Repetitions"),
                    Design.Spacer(),
                    self.configWidgets["repeats"],
                ),
                Design.Spacer(),
                Design.HBox(Design.Spacer(), self.jsonButton),
            )
        )

    def segmentValueChange(self, valueName, newValue):
        if valueName == "duration":
            newValue["text"] = f'{float(newValue["text"]):.3f}'
        super(Subsequence, self).segmentValueChange(valueName, newValue)


class TriggerWait(Widget):
    def __init__(self, sequence: Sequence, name):
        super(TriggerWait, self).__init__(sequence, name)

        self.configWidgets["input_ttl"] = Input.ComboBox(
            itemsGenerateFunction=self.getTTLInputDevices,
            default=crate.Sequences.segmentGet(self.sequence.name, self.name, "input_ttl"),
            changedCallback=lambda value: crate.Sequences.SegmentValueChange(self.sequence.name, self.name, "input_ttl", value),
        )

        self.contentWidget.layout().addWidget(
            Design.VBox(
                QtW.QLabel("Input TTL"),
                self.configWidgets["input_ttl"],
                Design.Spacer(),
                Design.HBox(Design.Spacer(), self.jsonButton),
            )
        )

    def getTTLInputDevices(self):
        return [portName for portName, portData in crate.labsetup.items() if "module" in portData and portData["module"] == "artiq.coredevice.ttl" and crate.device_db[portData["device"]]["class"] == "TTLInOut"]
