import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Segment as Segment
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.TableSequenceView as TableSequenceView
import gui.widgets.Viewer as Viewer


class Widget(QtW.QScrollArea):
    def __init__(self, name, dock):
        super(Widget, self).__init__()
        self.name = name
        self.dock = dock
        self.segmentList = Design.DragableItemList(QtC.Qt.Orientation.Horizontal)
        self.segmentList.contextMenuEvent = self.contextMenuEvent
        self.segmentList.onIndexingChanged = lambda segName, oldIndex, newIndex: crate.Sequences.SegmentIndexChange(self.name, segName, oldIndex, newIndex)
        self.rowHeights = {}
        self.setWidgetResizable(True)
        self.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.setWidget(
            Design.HBox(
                self.segmentList,
                Design.VBox(Design.Spacer(), Viewer.InfoButton(crate.sequences[self.name])),
            )
        )
        for segName, segData in crate.sequences[self.name]["segments"].items():
            self.addNewSegment(segName, segData, noAlign=True)
        self.alignPorts()
        self.alignDescriptions()

    def contextMenuEvent(self, e):
        menu = QtW.QMenu()
        menu.addAction("New Portstates").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.name, segData={"type": "portstate"}))
        menu.addAction("New Subsequence").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.name, segData={"type": "subsequence"}))
        menu.addAction("New TriggerWait").triggered.connect(lambda: crate.Sequences.SegmentAdd(self.name, segData={"type": "triggerwait"}))
        menu.exec(self.mapToGlobal(e.pos()))

    def addNewSegment(self, segName, segData, index=None, noAlign=False):
        segmentClass = Segment.Subsequence if segData["type"] == "subsequence" else (Segment.TriggerWait if segData["type"] == "triggerwait" else Segment.PortStates)
        segment = segmentClass(self, segName)
        self.segmentList.add(segment, index=index)
        self.segmentList.items[segName] = segment
        if not noAlign:
            self.alignPorts()
            self.alignDescriptions()
        TableSequenceView.updateTable()

    def deleteSegment(self, segName):
        segment = self.segmentList.items.pop(segName)
        self.segmentList.remove(segment)
        segment.deleteLater()
        self.alignPorts()
        self.alignDescriptions()
        TableSequenceView.updateTable()

    def segmentIndexChanged(self, segName, newIndex):
        self.segmentList.changeIndex(segName, newIndex)
        TableSequenceView.updateTable()

    def alignPorts(self, value=None):
        if value is None:
            value = crate.Config.getDockConfig(SequenceEditor.title, SequenceEditor.align_ports)
        for segment in self.segments():
            if type(segment) is Segment.PortStates:
                segment.dealignPorts()
        if not value:
            return
        portHeightBlocks = {portName: 0 for portName in crate.labsetup}
        rpcHeightBlocks = {rpcName: 0 for rpcName in crate.rpcs}
        for segment in self.segments():
            if type(segment) is Segment.PortStates:
                for portName, portWidget in segment.portStateWidgets.items():
                    portHeightBlocks[portName] = max(portHeightBlocks[portName], portWidget.getHeightBlocks())
                for rpcName, rpcWidget in segment.rpcWidgets.items():
                    rpcHeightBlocks[rpcName] = max(rpcHeightBlocks[rpcName], rpcWidget.getHeightBlocks())
        for segment in self.segments():
            if type(segment) is Segment.PortStates:
                segment.alignPorts(portHeightBlocks, rpcHeightBlocks)

    def alignDescriptions(self, value=None):
        if value is None:
            value = crate.Config.getDockConfig(SequenceEditor.title, SequenceEditor.align_ports)
        for segment in self.segments():
            segment.configWidgets["description"].setMinimumHeight(0)
        if not value:
            return

        def afterPaintAlignDescriptions():
            descriptionHeight = 0
            for segment in self.segments():
                descriptionHeight = max(descriptionHeight, segment.configWidgets["description"].height())
            for segment in self.segments():
                segment.configWidgets["description"].setMinimumHeight(descriptionHeight)

        QtC.QTimer.singleShot(0, afterPaintAlignDescriptions)

    def updateShowFullPortnames(self, value):
        for segment in self.segments():
            if type(segment) is Segment.PortStates:
                segment.showFullPortnames(value)

    def segments(self):
        return self.segmentList.getItemList()

    def getSegment(self, name):
        return self.segmentList.items[name]
