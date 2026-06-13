import copy

import gui.crate as crate
import gui.crate.FileManager
import gui.widgets.Variables

DEFAULT_VALUES = {
    "value": "0",
}


def getValue(variableName, valueName):
    variable = crate.variables[variableName]
    if valueName not in variable:
        if valueName == "alias":
            variable[valueName] = variableName.split("/")[-1]
        else:
            variable[valueName] = copy.deepcopy(DEFAULT_VALUES[valueName])
    return variable[valueName]


class Add(crate.Actions.Add):
    def __init__(self, variableName, variableData):
        if "value" not in variableData:
            variableData["value"] = "0"
        if "alias" not in variableData:
            variableData["alias"] = variableName.split("/")[-1]
        super(Add, self).__init__(variableName, variableData)

    def description(variableName):
        return f"{gui.widgets.Variables.title}: Variable {variableName} added"

    def do(action):
        crate.variables[action["name"]] = action["data"]
        crate.FileManager.saveVariables()
        gui.widgets.Variables.dock.addItem(action["name"], isDir=action["data"]["isDir"])

    def inverseAction():
        return Delete


class Delete(crate.Actions.Delete):
    def __init__(self, variableName):
        super(Delete, self).__init__(variableName, crate.variables[variableName])

    def description(variableName):
        return f"{gui.widgets.Variables.title}: Variable {variableName} deleted"

    def do(action):
        crate.variables.pop(action["name"])
        crate.FileManager.saveVariables()
        gui.widgets.Variables.dock.deleteItem(action["name"])

    def inverseAction():
        return Add


class Rename(crate.Actions.Rename):
    def __init__(self, oldName, newName):
        super(Rename, self).__init__(oldName, newName)

    def description(oldName, newName):
        return f"{gui.widgets.Variables.title}: Variable {oldName} renamed to {newName}"

    def do(action):
        crate.Actions.Rename.do(
            crate.variables,
            Rename.updateData,
            [gui.crate.FileManager.saveVariables],
            gui.widgets.Variables.dock.renameItem,
            action,
        )

    def updateData(oldName, newName):
        crate.variables[newName] = crate.variables.pop(oldName)


class ValueChange(crate.Actions.ValueChange):
    def __init__(self, variableName, valueName, newValue):
        oldValue = crate.variables[variableName][valueName]
        if oldValue == newValue:
            return
        super(ValueChange, self).__init__(variableName, valueName, oldValue, newValue)

    def description(variableName, valueName, oldValue, newValue):
        return f"{gui.widgets.Variables.title}: Variable {variableName}: Changed {valueName} from {oldValue} to {newValue}"

    def do(action):
        crate.variables[action["name"]][action["valuename"]] = action["newvalue"]
        gui.crate.FileManager.saveVariables()
        gui.widgets.Variables.dock.widgetValueChange(action["name"], action["valuename"], action["newvalue"])
