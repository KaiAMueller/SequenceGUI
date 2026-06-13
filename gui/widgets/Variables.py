import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Dock as Dock
import gui.widgets.Input as Input
import gui.widgets.MultiRun as MultiRun
import gui.widgets.Viewer as Viewer


def replacer(text):
    variableDataIterator = crate.variables.values() if MultiRun.currentlyRunningVariables is None else MultiRun.currentlyRunningVariables.values()
    changed = True
    counter = 0
    while changed:
        changed = False
        for variableData in variableDataIterator:
            if not variableData["isDir"]:
                if variableData["alias"] in text:
                    text = text.replace(variableData["alias"], variableData["value"])
                    changed = True
        counter += 1
        if counter > 100:
            raise ValueError(f"Infinite loop in variable: {text}")
    return text


dock = None
title = "🔤 Variables"


class Dock(Dock.ListConfigDockExtension):
    def __init__(self, gui):
        super(Dock, self).__init__(
            title=title,
            gui=gui,
            widgetClass=Widget,
            itemKind="Variable",
            backendCallbacks=crate.Variables,
            icon="🔤",
        )
        global dock
        dock = self

    def loadCrate(self):
        super(Dock, self).loadCrate(crate.variables)


class Widget(Design.VBox):
    def __init__(self, name, dock):
        self.name = name
        self.dock = dock
        self.defaultValueField = Input.TextField(
            default=crate.Variables.getValue(self.name, "value"),
            replacer=replacer,
            reader=str,
            changedCallback=lambda value: crate.Variables.ValueChange(self.name, "value", value),
            dontUpdateMetrics=True,
        )
        self.aliasField = Input.TextField(
            default=crate.Variables.getValue(self.name, "alias"),
            reader=self.aliasReader,
            changedCallback=lambda value: crate.Variables.ValueChange(self.name, "alias", value),
            dontUpdateMetrics=True,
        )
        self.valueFields = {
            "value": self.defaultValueField,
            "alias": self.aliasField,
        }
        super(Widget, self).__init__(
            Design.HBox(QtW.QLabel("default value"), 1, self.defaultValueField),
            Design.HBox(QtW.QLabel("alias"), 1, self.aliasField),
            Design.Spacer(),
            Design.HBox(Design.Spacer(), Viewer.InfoButton(crate.variables[self.name])),
        )

    def aliasReader(self, alias):
        try:
            float(alias)
            return None
        except ValueError:
            pass
        for variableName, variableData in crate.variables.items():
            if self.name == variableName:
                continue
            if variableData["isDir"]:
                continue
            alias2 = crate.Variables.getValue(variableName, "alias")
            if alias in alias2 or alias2 in alias:
                return None
        return alias

    def valueChange(self, valueName, value):
        self.valueFields[valueName].set(value)
