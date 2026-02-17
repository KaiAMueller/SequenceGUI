import copy

import gui.crate as crate
import gui.crate.Actions as Actions
import gui.crate.FileManager as FileManager
import gui.widgets.MultiRun

DEFAULT_VALUES = {
    "mode": "scan",
    "dimensions": {},
}

DEFAULT_DIMENSION_VALUES = {
    "variables": {},
    "steps": "10",
}


DEFAULT_VARIABLE_VALUES = {
    "mode": "linear",
    "min": "0",
    "max": "1",
    "datalist": [0, 1, 2, 3],
}


def getValue(multirunName, valueName):
    multirun = crate.multiruns[multirunName]
    if valueName not in multirun:
        multirun[valueName] = copy.deepcopy(DEFAULT_VALUES[valueName])
    return multirun[valueName]

def getDimensionValue(multirunName, dimension, valueName):
    dimensionData = crate.multiruns[multirunName]["dimensions"][dimension]
    if valueName not in dimensionData:
        dimensionData[valueName] = copy.deepcopy(DEFAULT_DIMENSION_VALUES[valueName])
    return dimensionData[valueName]


def getVariableValue(multirunName, dimension, variableName, valueName):
    variable = crate.multiruns[multirunName]["dimensions"][dimension]["variables"][variableName]
    if valueName not in variable:
        variable[valueName] = copy.deepcopy(DEFAULT_VARIABLE_VALUES[valueName])
    return variable[valueName]


class Add(Actions.Add):
    def __init__(self, multirunName, multirunData):
        super(Add, self).__init__(multirunName, multirunData)

    def description(multirunName):
        return f"{gui.widgets.MultiRun.title}: Multirun {multirunName} added"

    def do(action):
        crate.multiruns[action["name"]] = action["data"]
        FileManager.saveMultiRuns()
        gui.widgets.MultiRun.dock.addItem(action["name"], isDir=action["data"]["isDir"])

    def inverseAction():
        return Delete


class Delete(Actions.Delete):
    def __init__(self, multirunName):
        super(Delete, self).__init__(multirunName, crate.multiruns[multirunName])

    def description(multirunName):
        return f"{gui.widgets.MultiRun.title}: Multirun {multirunName} deleted"

    def do(action):
        crate.multiruns.pop(action["name"])
        FileManager.saveMultiRuns()
        gui.widgets.MultiRun.dock.deleteItem(action["name"])

    def inverseAction():
        return Add


class Rename(Actions.Rename):
    def __init__(self, oldName, newName):
        super(Rename, self).__init__(oldName, newName)

    def description(oldName, newName):
        return f"{gui.widgets.MultiRun.title}: Multirun {oldName} renamed to {newName}"

    def do(action):
        Actions.Rename.do(
            crate.multiruns,
            Rename.updateData,
            [FileManager.saveMultiRuns],
            gui.widgets.MultiRun.dock.renameItem,
            action,
        )

    def updateData(oldName, newName):
        crate.multiruns[newName] = crate.multiruns.pop(oldName)


class ValueChange(Actions.ValueChange):
    def __init__(self, multirunName, valueName, newValue):
        oldValue = crate.multiruns[multirunName][valueName]
        if oldValue == newValue:
            return
        super(ValueChange, self).__init__(multirunName, valueName, oldValue, newValue)

    def description(multirunName, valueName, oldValue, newValue):
        return f"{gui.widgets.MultiRun.title}: Multirun {valueName}: Changed {valueName} from {oldValue} to {newValue}"

    def do(action):
        crate.multiruns[action["name"]][action["valuename"]] = action["newvalue"]
        FileManager.saveMultiRuns()
        gui.widgets.MultiRun.dock.widgetValueChange(action["name"], action["valuename"], action["newvalue"])


class DimensionAdd(Actions.Action):
    def __init__(self, name, index=None, data={}):
        if index is None:
            index = "dim0"
            while index in crate.multiruns[name]["dimensions"]:
                index = "dim" + str(int(index[3:]) + 1)
        super(DimensionAdd, self).__init__(name=name, index=index, data=data)

    @classmethod
    def action(cls, name, index, data):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, index),
            "name": name,
            "index": index,
            "data": copy.deepcopy(data),
        }

    def description(name, index):
        return f"{gui.widgets.MultiRun.title}: Multirun {name}: Dimension {index} added."

    @classmethod
    def inverse(cls, action):
        return DimensionDelete.action(action["name"], action["index"], action["data"])

    def do(action):
        crate.multiruns[action["name"]]["dimensions"][action["index"]] = action["data"]
        FileManager.saveMultiRuns()
        if gui.widgets.MultiRun.dock.configWidget.name == action["name"]:
            gui.widgets.MultiRun.dock.configWidget.addDimensionWidget(action["index"])


class DimensionDelete(Actions.Action):
    def __init__(self, name, index):
        super(DimensionDelete, self).__init__(name=name, index=index, data=crate.multiruns[name]["dimensions"][index])

    @classmethod
    def action(cls, name, index, data):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, index),
            "name": name,
            "index": index,
            "data": copy.deepcopy(data),
        }

    def description(name, index):
        return f"{gui.widgets.MultiRun.title}: Multirun {name}: Dimension {index} deleted."

    @classmethod
    def inverse(cls, action):
        return DimensionAdd.action(action["name"], action["index"], action["data"])

    def do(action):
        crate.multiruns[action["name"]]["dimensions"].pop(action["index"])
        FileManager.saveMultiRuns()
        if gui.widgets.MultiRun.dock.configWidget.name == action["name"]:
            gui.widgets.MultiRun.dock.configWidget.deleteDimensionWidget(action["index"])

class DimensionValueChange(Actions.Action):
    def __init__(self, name, index, valueName, newValue):
        oldValue = crate.multiruns[name]["dimensions"][index][valueName]
        if oldValue == newValue:
            return
        super(DimensionValueChange, self).__init__(
            name=name,
            index=index,
            valueName=valueName,
            oldValue=oldValue,
            newValue=newValue,
        )

    @classmethod
    def action(cls, name, index, valueName, oldValue, newValue):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, index, valueName, oldValue, newValue),
            "name": name,
            "index": index,
            "valuename": valueName,
            "oldvalue": oldValue,
            "newvalue": newValue,
        }

    def description(name, index, valueName, oldValue, newValue):
        return f"{gui.widgets.MultiRun.title}: Multirun {name}: Dimension {index}: Changed {valueName} from {str(oldValue)} to {str(newValue)}"

    @classmethod
    def inverse(cls, action):
        return DimensionValueChange.action(
            action["name"],
            action["index"],
            action["valuename"],
            action["newvalue"],
            action["oldvalue"],
        )

    def do(action):
        crate.multiruns[action["name"]]["dimensions"][action["index"]][action["valuename"]] = action["newvalue"]
        FileManager.saveMultiRuns()
        if gui.widgets.MultiRun.dock.configWidget.name == action["name"]:
            gui.widgets.MultiRun.dock.configWidget.dimensionWidgets[action["index"]].valueChange(action["valuename"], action["newvalue"])



class VariableAdd(Actions.Action):
    def __init__(self, name, dimension, variableName, variableData={}):
        super(VariableAdd, self).__init__(
            name=name,
            dimension=dimension,
            variableName=variableName,
            variableData=variableData,
        )

    @classmethod
    def action(cls, name, dimension, variableName, variableData):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, dimension, variableName),
            "name": name,
            "dimension": dimension,
            "variablename": variableName,
            "variabledata": copy.deepcopy(variableData),
        }

    def description(name, dimension, variableName):
        return f"{gui.widgets.MultiRun.title}: Multirun {name}: Dimension {dimension}: Variable {variableName} added."

    @classmethod
    def inverse(cls, action):
        return VariableDelete.action(
            action["name"],
            action["dimension"],
            action["variablename"],
            action["variabledata"],
        )

    def do(action):
        crate.multiruns[action["name"]]["dimensions"][action["dimension"]]["variables"][action["variablename"]] = action["variabledata"]
        FileManager.saveMultiRuns()
        if gui.widgets.MultiRun.dock.configWidget.name == action["name"]:
            gui.widgets.MultiRun.dock.configWidget.dimensionWidgets[action["dimension"]].addVariableWidget(action["variablename"])


class VariableDelete(Actions.Action):
    def __init__(self, name, dimension, variableName):
        super(VariableDelete, self).__init__(
            name=name,
            dimension=dimension,
            variableName=variableName,
            variableData=crate.multiruns[name]["dimensions"][dimension]["variables"][variableName],
        )

    @classmethod
    def action(cls, name, dimension, variableName, variableData):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, dimension, variableName),
            "name": name,
            "dimension": dimension,
            "variablename": variableName,
            "variabledata": copy.deepcopy(variableData),
        }

    def description(name, dimension, variableName):
        return f"{gui.widgets.MultiRun.title}: Multirun {name}: Dimension {dimension}: Variable {variableName} deleted."

    @classmethod
    def inverse(cls, action):
        return VariableAdd.action(
            action["name"],
            action["dimension"],
            action["variablename"],
            action["variabledata"],
        )

    def do(action):
        crate.multiruns[action["name"]]["dimensions"][action["dimension"]]["variables"].pop(action["variablename"])
        FileManager.saveMultiRuns()
        if gui.widgets.MultiRun.dock.configWidget.name == action["name"]:
            gui.widgets.MultiRun.dock.configWidget.dimensionWidgets[action["dimension"]].deleteVariableWidget(action["variablename"])


class VariableValueChange(Actions.Action):
    def __init__(self, name, dimension, variableName, valueName, newValue):
        oldValue = crate.multiruns[name]["dimensions"][dimension]["variables"][variableName][valueName]
        if oldValue == newValue:
            return
        super(VariableValueChange, self).__init__(
            name=name,
            dimension=dimension,
            variableName=variableName,
            valueName=valueName,
            oldValue=oldValue,
            newValue=newValue,
        )

    @classmethod
    def action(cls, name, dimension, variableName, valueName, oldValue, newValue):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, dimension, variableName, valueName, oldValue, newValue),
            "name": name,
            "dimension": dimension,
            "variablename": variableName,
            "valuename": valueName,
            "oldvalue": oldValue,
            "newvalue": newValue,
        }

    def description(name, dimension, variableName, valueName, oldValue, newValue):
        return f"{gui.widgets.MultiRun.title}: Multirun {name}: Dimension {dimension}: Variable {variableName}: Changed {valueName} from {str(oldValue)} to {str(newValue)}"

    @classmethod
    def inverse(cls, action):
        return VariableValueChange.action(
            action["name"],
            action["dimension"],
            action["variablename"],
            action["valuename"],
            action["newvalue"],
            action["oldvalue"],
        )

    def do(action):
        crate.multiruns[action["name"]]["dimensions"][action["dimension"]]["variables"][action["variablename"]][action["valuename"]] = action["newvalue"]
        FileManager.saveMultiRuns()
        if gui.widgets.MultiRun.dock.configWidget.name == action["name"]:
            gui.widgets.MultiRun.dock.configWidget.dimensionWidgets[action["dimension"]].variableWidgets[action["variablename"]].valueChange(action["valuename"], action["newvalue"])
