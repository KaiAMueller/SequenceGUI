import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW
from PySide6.QtGui import QDrag

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.SequenceEditor as SequenceEditor
import gui.widgets.TableSequenceView as TableSequenceView
import gui.widgets.Viewer as Viewer


# ABSTRACT CLASS - OVERRIDDEN BY CLASSES FOR SPECIFIC MODULE, e.g. TTL, URUKUL...
class Widget(Design.HBox):
    def __init__(self, segment, portName, configDialogClass):
        self.segment = segment
        self.portName = portName
        self.configDialogClass = configDialogClass
        self.configDialog = None
        self.show_full_portname = crate.Config.getDockConfig(SequenceEditor.title, SequenceEditor.show_full_portnames)
        self.complementStateData()

        # text label widget
        self.textLabel = QtW.QLabel("")
        self.textLabel.setFont(Design.SmallLabelFont())
        self.updateLabel()

        # preview widget
        self.previewWidget = self.generatePreviewWidget()
        self.previewWidget.setFont(Design.SmallValueFont())

        # configuration widgets
        self.configWidgets = {}

        super(Widget, self).__init__(
            self.textLabel,
            Design.Spacer(),
            self.previewWidget,
        )

    def updateName(self, newName):
        self.portName = newName
        self.updateLabel()

    def showFullPortname(self, value):
        self.show_full_portname = value
        self.updateLabel()

    def updateLabel(self):
        if self.show_full_portname:
            self.textLabel.setText(self.portName)
        else:
            self.textLabel.setText(self.portName.split("/")[-1])

    def valueChange(self, valueName, newValue):
        self.configWidgets[valueName].set(newValue)
        self.updatePreviewWidget()
        if self.configDialog is not None:
            self.configDialog.updateVisibility()
        TableSequenceView.updateTable()

    def openConfigButtonClicked(self):
        self.openConfig()

    def openConfig(self):
        if self.configDialog is None:
            self.configDialog = self.configDialogClass(self)
            self.configDialog.exec()

    def closeConfig(self):
        self.configDialog.isAboutToClose = True
        if self.configDialog is not None:
            for configWidget in self.configWidgets.values():
                configWidget.setParent(self)
                configWidget.setVisible(False)
            self.configDialog.close()
            self.configDialog = None

    def generatePreviewWidget(self):
        widget = Design.Button("not implemented", flat=False, size="medium")
        widget.clicked.connect(self.openConfigButtonClicked)
        widget.onRightClick = self.openConfigButtonClicked
        return widget

    def updatePreviewWidget(self):
        pass

    def complementStateData(self):
        pass

    def getHeightBlocks(self):
        return 1 + self.previewWidget.text().count("\n") / 2

    def getValue(self, valueName):
        return crate.Sequences.getPortStateValue(self.segment.sequence.name, self.segment.name, self.portName, valueName)

    def getData(self):
        return crate.sequences[self.segment.sequence.name]["segments"][self.segment.name]["ports"][self.portName]
        
    def getChangedCallback(self, valueName):
        return lambda value: crate.Sequences.PortStateValueChange(
            self.segment.sequence.name,
            self.segment.name,
            self.portName,
            valueName,
            value,
        )
    def mouseMoveEvent(self, e):
        if crate.Config.getDockConfig(SequenceEditor.title, SequenceEditor.rearrangable_portstates) and e.buttons() == QtC.Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QtC.QMimeData()
            mime.setText(self.portName) #assign a name
            drag.setMimeData(mime)
            drag.exec(QtC.Qt.DropAction.MoveAction)
            self.simulateMouseRelease() #fixes stuck left mouse button
            
    def simulateMouseRelease(widget):
        # Get the position in the widget's coordinate space
        pos = QtC.QPoint(widget.width() / 2, widget.height() / 2)
        
        # Create a mouse release event
        releaseEvent = QtG.QMouseEvent(
            QtG.QMouseEvent.MouseButtonRelease,
            pos,
            QtC.Qt.LeftButton,
            QtC.Qt.NoButton,
            QtC.Qt.NoModifier
        )
        QtW.QApplication.postEvent(widget, releaseEvent)


# ABSTRACT CLASS - OVERRIDDEN BY CLASSES FOR SPECIFIC MODULE, e.g. TTL, URUKUL...
class ConfigDialog(Design.DialogDesign):
    def __init__(self, portStateWidget):
        title = f"{portStateWidget.portName} Config"
        super(ConfigDialog, self).__init__(title, "⚙", closeButtonEnabled=False)
        self.portStateWidget = portStateWidget
        self.portName = portStateWidget.portName
        self.segment = portStateWidget.segment
        self.configWidgets = portStateWidget.configWidgets
        self.isAboutToClose = False

        # event filter for undo/redo shortcuts
        self.installEventFilter(self)

        # window title
        self.setWindowTitle(title)

        # delete button
        self.deleteButton = Design.DeleteButton("Delete Port State")
        self.deleteButton.clicked.connect(self.deleteButtonClicked)

        # save button
        self.doneButton = Design.Button(" Done ")
        self.doneButton.clicked.connect(self.doneButtonClicked)

        # layout
        self.layout().addWidget(
            Design.VBox(
                self.generateConfigurationWidgets(),
                Design.Spacer(),
                Design.HBox(
                    Design.Spacer(),
                    Viewer.InfoButton(crate.sequences[self.segment.sequence.name]["segments"][self.segment.name]["ports"][self.portName]),
                ),
                Design.HBox(1, self.doneButton, self.deleteButton),
            )
        )

        self.updateVisibility()
        self.doneButton.setFocus()

    # event filter for undo/redo shortcuts
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
        crate.Sequences.PortStateDelete(self.segment.sequence.name, self.segment.name, self.portName)

    def doneButtonClicked(self):
        for configWidget in self.configWidgets.values():
            if hasattr(configWidget, "onEditingFinished"):
                # trigger editingFinished signal manually because
                # otherwise it triggers only after the config closes
                # which calls then updatevisibility after its closed
                # which makes it appear somewhere else (visual bug)
                configWidget.onEditingFinished()
        self.portStateWidget.closeConfig()

    def generateConfigurationWidgets(self):
        return QtW.QWidget()

    def updateVisibility(self):
        pass
