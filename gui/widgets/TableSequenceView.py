import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.settings as settings
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Dock
import gui.widgets.Formula as Formula
import gui.widgets.Input as Input
import gui.widgets.PortState as PortState
import gui.widgets.Variables as Variables
from gui.widgets.Log import log

dock = None
sequenceEditorDock = None
title = "🧮 Table Sequence View"
show_all_ports = "Show all ports"
expand_subsequences = "Expand subsequences"


def updateTable(ignore=None):
    # traceback.print_stack()
    dock.toRender = True


def setSequenceEditorDock(dock):
    global sequenceEditorDock
    sequenceEditorDock = dock


class Dock(gui.widgets.Dock.Dock):
    def __init__(self, gui):
        super(Dock, self).__init__(title, gui)
        global dock
        dock = self

        self.addSettingsAction(
            show_all_ports,
            lambda checked: crate.Config.ValueChange(title, show_all_ports, checked),
            crate.Config.getDockConfig(title, show_all_ports),
        )
        self.addSettingsAction(
            expand_subsequences,
            lambda checked: crate.Config.ValueChange(title, expand_subsequences, checked),
            crate.Config.getDockConfig(title, expand_subsequences),
        )

        self.scrollArea = QtW.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(QtC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setFrameStyle(QtW.QFrame.Shape.NoFrame)
        self.setWidget(self.scrollArea)
        # self.setWidget(QtW.QLabel(f"Not available yet in 0.4-beta. Soon."))

        self.renderLimit = 50
        self.renderWarningLabel = QtW.QLabel()
        self.renderAnywayButton = Design.Button("Render Anyway")
        self.renderAnywayButton.clicked.connect(self.renderAnywayButtonClicked)
        self.renderWarningDontAskAgainCheckbox = QtW.QCheckBox("Don't ask again for this size")
        self.renderWarningWidget = Design.HBox(
            Design.VBox(
                Design.Frame(
                    Design.VBox(
                        self.renderWarningLabel,
                        self.renderWarningDontAskAgainCheckbox,
                        self.renderAnywayButton,
                    )
                ),
                Design.Spacer(),
            ),
            Design.Spacer(),
        )
        self.renderWarningWidget.resize(300, 200)
        self.renderWarningWidget.setVisible(False)

        self.tableWidget = QtW.QTableWidget()
        self.tableWidget.setHorizontalScrollBarPolicy(QtC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget.setContentsMargins(0, 0, 0, 0)

        def customMousePressEvent(
            event,
        ):  # because default doesnt have right click event
            if event.button() == QtC.Qt.MouseButton.LeftButton:
                self.onCellLeftClicked(int(event.position().x()), int(event.position().y()))
            elif event.button() == QtC.Qt.MouseButton.RightButton:
                self.onCellRightOrDoubleClicked(int(event.position().x()), int(event.position().y()))

        def customMouseDoubleClickEvent(event):
            self.onCellRightOrDoubleClicked(int(event.position().x()), int(event.position().y()))

        self.tableWidget.mouseDoubleClickEvent = customMouseDoubleClickEvent
        self.tableWidget.mousePressEvent = customMousePressEvent
        self.tableWidget.setShowGrid(True)
        self.tableWidget.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self.tableWidget.verticalHeader().setSectionResizeMode(QtW.QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QtW.QHeaderView.ResizeMode.ResizeToContents)
        self.sequenceNameLabelSpace = [Design.HBox(spacing=0) for i in range(5)]
        self.scrollArea.setWidget(
            Design.VBox(
                *([self.renderWarningWidget] + [self.sequenceNameLabelSpace[i] for i in range(5)] + [self.tableWidget]),
                spacing=0,
            )
        )

        self.toRender = False
        self.lastRenderTime = QtC.QDateTime.currentDateTime().toMSecsSinceEpoch()

        QtC.QTimer.singleShot(20, self.checkToRenderLoop)

    def checkToRenderLoop(self):
        QtC.QTimer.singleShot(20, self.checkToRenderLoop)
        if self.toRender:
            if QtC.QDateTime.currentDateTime().toMSecsSinceEpoch() - self.lastRenderTime > 50:
                try:
                    self.renderTable()
                except Exception as e:
                    log("Error rendering table sequence view: ")
                    log(e)
                self.lastRenderTime = QtC.QDateTime.currentDateTime().toMSecsSinceEpoch()

    def renderAnywayButtonClicked(self):
        if self.renderWarningDontAskAgainCheckbox.isChecked():
            self.renderLimit *= 2
        self.renderTable(
            forceRender=True,
            increaseRenderLimit=self.renderWarningDontAskAgainCheckbox.isChecked(),
        )

    def renderTable(self, forceRender=False, increaseRenderLimit=False):
        if not crate.loadDone or not self.isVisible() or sequenceEditorDock is None:
            return
        self.toRender = False

        # return

        sequenceName = sequenceEditorDock.list.currentSelection

        # clear table
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setRowCount(1)
        for i in range(5):
            for j in reversed(range(self.sequenceNameLabelSpace[i].layout().count())):
                self.sequenceNameLabelSpace[i].layout().itemAt(j).widget().deleteLater()

        if sequenceName is None or crate.sequences[sequenceName]["isDir"]:
            self.tableWidget.setVisible(False)
            self.renderWarningWidget.setVisible(False)
            return
        else:
            self.tableWidget.setVisible(True)

        if not crate.Config.getDockConfig(title, expand_subsequences):
            segmentDicts = [
                {
                    "seqName": sequenceName,
                    "segData": segData,
                    "segName": segName,
                    "header": util.unitValueToText(segData["duration"]),
                    "sequences_begin": [None] * 5,
                    "sequences_end": [None] * 5,
                }
                for segName, segData in crate.sequences[sequenceName]["segments"].items()
                if segData["enabled"]
            ]
        else:
            toExpandSegmentDicts = [
                {
                    "seqName": sequenceName,
                    "segData": segData,
                    "segName": segName,
                    "header": util.unitValueToText(segData["duration"]),
                    "sequences_begin": [None] * 5,
                    "sequences_end": [None] * 5,
                }
                for segName, segData in crate.sequences[sequenceName]["segments"].items()
                if segData["enabled"]
            ]
            for i in range(5):  # expand up to 5 levels of subsequences
                segmentDicts = []
                for segDict in toExpandSegmentDicts:
                    seqName = segDict["seqName"]
                    segData = segDict["segData"]
                    segName = segDict["segName"]
                    if not segData["enabled"]:
                        continue
                    if segData["type"] in ["portstate", "triggerwait"]:
                        segmentDicts += [
                            {
                                "seqName": seqName,
                                "segData": segData,
                                "segName": segName,
                                "header": util.unitValueToText(segData["duration"]),
                                "sequences_begin": segDict["sequences_begin"],
                                "sequences_end": segDict["sequences_end"],
                            }
                        ]
                    elif segData["type"] == "subsequence":
                        if segData["subsequence"] is None or segData["subsequence"] == "" or "inf" in segData["duration"]["text"]:
                            self.tableWidget.setItem(0, 0, TableWidgetItem("Sequence contains infinite loop"))
                            return
                        repeats = Input.getValueFromState(segData["repeats"], reader=int, replacer=Variables.replacer)
                        if repeats is not None:
                            for j in range(repeats):
                                expansion = [
                                    {
                                        "seqName": segData["subsequence"],
                                        "segData": subSegData,
                                        "segName": subSegName,
                                        "header": util.unitValueToText(subSegData["duration"]),
                                        "sequences_begin": [None] * 5,
                                        "sequences_end": [None] * 5,
                                    }
                                    for subSegName, subSegData in crate.sequences[segData["subsequence"]]["segments"].items()
                                    if subSegData["enabled"]
                                ]
                                if len(expansion) > 0:
                                    expansion[0]["sequences_begin"] = segDict["sequences_begin"].copy()
                                    expansion[0]["sequences_begin"][i] = segData["subsequence"]
                                    expansion[len(expansion) - 1]["sequences_end"] = segDict["sequences_end"].copy()
                                    expansion[len(expansion) - 1]["sequences_end"][i] = segData["subsequence"]
                                segmentDicts += expansion
                toExpandSegmentDicts = segmentDicts.copy()

        if len(segmentDicts) > self.renderLimit and not forceRender:
            self.renderWarningLabel.setText(f"Sequence has {len(segmentDicts)} steps.\nThis may take a while to display in TableSequenceView.\nStill want to render?")
            self.renderWarningWidget.setVisible(True)
            self.tableWidget.setVisible(False)
            return

        if increaseRenderLimit:
            self.renderLimit = max(self.renderLimit, int(len(segmentDicts) * 1.5 + 1))

        self.renderWarningWidget.setVisible(False)
        self.tableWidget.setVisible(True)

        self.tableWidget.setColumnCount(len(segmentDicts))
        self.tableWidget.setHorizontalHeaderLabels([segDict["header"] for segDict in segmentDicts])
        self.tableWidget.horizontalHeader().setMinimumSectionSize(5)

        if crate.Config.getDockConfig(title, show_all_ports):
            portNames = [portName for portName in crate.labsetup.keys() if not crate.labsetup[portName]["isDir"]]
        else:
            portNames = []
            for portName in crate.labsetup.keys():
                if crate.labsetup[portName]["isDir"]:
                    continue
                for segDict in segmentDicts:
                    segData = segDict["segData"]
                    if segData["type"] == "portstate":
                        if portName in segData["ports"]:
                            portNames.append(portName)
                            break
                    elif segData["type"] == "triggerwait":
                        if portName == segData["input_ttl"]:
                            portNames.append(portName)
                            break

        self.tableWidget.setRowCount(len(portNames))
        self.tableWidget.setVerticalHeaderLabels(portNames)
        

        leftNeighboor = [None] * len(portNames)
        for j, segDict in enumerate(segmentDicts):
            segData = segDict["segData"]
            for i, port in enumerate(portNames):
                if segData["type"] == "subsequence":
                    item = TableWidgetItem("~", backgroundColor=(0.5, 0.5, 0.5))
                    self.tableWidget.setItem(i, j, item)
                    leftNeighboor[i] = None
                elif segData["type"] == "triggerwait":
                    if port == segData["input_ttl"]:
                        item = TableWidgetItem(
                            text="Trigger",
                            pixmapInfo=None,
                            backgroundColor=(0, 0, 1),
                            onRightClick=None,
                        )
                        self.tableWidget.setItem(i, j, item)
                        leftNeighboor[i] = item
                elif segData["type"] == "portstate":
                    if port in segData["ports"]:
                        openConfigCall = None
                        module = crate.labsetup[port]["module"]
                        portData = segData["ports"][port]
                        tv = PortState.CARD_TYPES[module].getTableViewInfo(portData)
                        item = TableWidgetItem(
                            text=tv["text"],
                            backgroundColor=tv["color"],
                            pixmapInfo=tv["pixmap"] if "pixmap" in tv else None,
                            nextText=tv["next_text"] if "next_text" in tv else None,
                            nextBackgroundColor=(tv["next_color"] if "next_color" in tv else None),
                            onRightClick=openConfigCall,
                        )
                        self.tableWidget.setItem(i, j, item)
                        leftNeighboor[i] = item
                    else:
                        nextText = leftNeighboor[i].nextText if leftNeighboor[i] is not None and leftNeighboor[i].nextText is not None else None
                        nextBackgroundColor = leftNeighboor[i].nextBackgroundColor if leftNeighboor[i] is not None and leftNeighboor[i].nextBackgroundColor is not None else None
                        item = TableWidgetItem(
                            text=nextText if nextText is not None else "",
                            color=(0.5, 0.5, 0.5),
                            backgroundColor=(nextBackgroundColor if nextBackgroundColor is not None else (0.5, 0.5, 0.5)),
                            nextText=nextText,
                            nextBackgroundColor=nextBackgroundColor,
                            onRightClick=None,
                        )
                        self.tableWidget.setItem(i, j, item)
                        
                        
        
        
        # finalize render after all sizes are set (20 ms should be one frame at 50+ fps)
        QtC.QTimer.singleShot(100, lambda: self.finalizeRendering(segmentDicts, portNames))
        
        
        
        

    def addGroupLabel(self, label, count):
        # Add group labels with a spacer between them
        self.leftLayout.addWidget(QtW.QLabel(label))
        for _ in range(count):
            self.leftLayout.addWidget(QtW.QLabel())  # Add a spacer for rows in this group
            
    def finalizeRendering(self, segmentDicts, portNames):
        lastX = [0] * 5
        for i in range(5):
            lastColumn = self.tableWidget.columnCount() - 1
            width = self.tableWidget.columnViewportPosition(lastColumn) + self.tableWidget.columnWidth(lastColumn) + self.tableWidget.verticalHeader().width() + 2
            self.sequenceNameLabelSpace[i].setFixedWidth(width)
            self.sequenceNameLabelSpace[i].setFixedHeight(0)
            spacer = QtW.QWidget()
            spacer.setFixedSize(self.tableWidget.verticalHeader().width() + 2, 15)
            self.sequenceNameLabelSpace[i].layout().addWidget(spacer)
            lastX[i] = self.tableWidget.verticalHeader().width() + 2

        for j in range(len(segmentDicts)):
            for i in range(len(portNames)):
                if self.tableWidget.item(i, j) is None:
                    continue
                self.tableWidget.item(i, j).renderPixmap(self.tableWidget.columnWidth(j), self.tableWidget.rowHeight(i))
            x = self.tableWidget.columnViewportPosition(j) + self.tableWidget.verticalHeader().width() + 2
            for i in range(5):
                if segmentDicts[j]["sequences_begin"][i] is not None:
                    self.sequenceNameLabelSpace[i].setFixedHeight(15)
                    spacer = QtW.QWidget()
                    spacer.setFixedSize(max(0, x - lastX[i]), 15)
                    self.sequenceNameLabelSpace[i].layout().addWidget(spacer)
                    lastX[i] = x
                if segmentDicts[j]["sequences_end"][i] is not None:
                    x_end = x + self.tableWidget.columnWidth(j)
                    label = QtW.QLabel(segmentDicts[j]["sequences_end"][i])
                    label.setObjectName("sequenceNameLabel")
                    label.setFixedSize(x_end - lastX[i], 15)
                    self.sequenceNameLabelSpace[i].layout().addWidget(label)
                    lastX[i] = x_end
        for i in range(5):
            self.sequenceNameLabelSpace[i].layout().addWidget(QtW.QWidget(), 1)

    def onCellLeftClicked(self, x, y):
        item = dock.tableWidget.itemAt(x, y)
        if item is not None:
            item.leftClicked()

    def onCellRightOrDoubleClicked(self, x, y):
        item = dock.tableWidget.itemAt(x, y)
        if item is not None:
            item.rightClicked()

    def configChange(self, option, value):
        super().configChange(option, value)
        updateTable()


def ThemeColor(color, theme_factor=1.0):
    if type(color) is QtG.QBrush or type(color) is QtG.QColor:
        return color
    if settings.getDarkmode():
        r = int(color[0] * 50 * theme_factor + (1 - theme_factor) * 255 * color[0])
        g = int(color[1] * 50 * theme_factor + (1 - theme_factor) * 255 * color[1])
        b = int(color[2] * 50 * theme_factor + (1 - theme_factor) * 255 * color[2])
    else:
        r = int((205 + color[0] * 50) * theme_factor + (1 - theme_factor) * 255 * color[0])
        g = int((205 + color[1] * 50) * theme_factor + (1 - theme_factor) * 255 * color[1])
        b = int((205 + color[2] * 50) * theme_factor + (1 - theme_factor) * 255 * color[2])
    return QtG.QColor(r, g, b)


class TableWidgetItem(QtW.QTableWidgetItem):
    def __init__(
        self,
        text,
        color=None,
        backgroundColor=None,
        onLeftClick=None,
        onRightClick=None,
        pixmapInfo=None,
        nextText=None,
        nextBackgroundColor=None,
    ):
        super().__init__(text)
        self.onLeftClick = onLeftClick
        self.onRightClick = onRightClick
        self.pixmapInfo = pixmapInfo
        self.nextText = nextText
        self.nextBackgroundColor = nextBackgroundColor
        if color is not None:
            self.setForeground(ThemeColor(color, 0.5))
        if backgroundColor is not None:
            self.setBackground(ThemeColor(backgroundColor))

    def leftClicked(self):
        if self.onLeftClick is not None:
            self.onLeftClick()

    def rightClicked(self):
        if self.onRightClick is not None:
            self.onRightClick()

    def renderPixmap(self, width, height):
        if self.pixmapInfo is not None:
            pixmap = Formula.generatePixmap(
                formula=self.pixmapInfo["formula"],
                w=width - 1,
                h=height - 1,
                x0=self.pixmapInfo["from"],
                x1=self.pixmapInfo["to"],
            )
            self.setData(QtC.Qt.ItemDataRole.BackgroundRole, pixmap)
