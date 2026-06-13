import copy

import gui.crate as crate


def inversePrePostActions(action):
    action["preactions"], action["postactions"] = (
        action["postactions"],
        action["preactions"],
    )
    action["preactions"] = [crate.inverseAction(a) for a in action["preactions"]]
    action["postactions"] = [crate.inverseAction(a) for a in action["postactions"]]
    action["preactions"].reverse()
    action["postactions"].reverse()


class Action:
    def __init__(self, **kwargs):
        cls = self.__class__
        action = cls.action(**kwargs)
        crate.appendToUndoStack(action)
        cls.do(action)

    def do(action):
        raise "not implemented"

    def inverse(action):
        raise "not implemented"


class Add(Action):
    def __init__(self, name, data):
        super(Add, self).__init__(name=name, data=data)

    @classmethod
    def action(cls, name, data):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name),
            "name": name,
            "data": copy.deepcopy(data),
        }

    def description(name):
        raise "not implemented"

    @classmethod
    def inverse(cls, action):
        return cls.inverseAction().action(action["name"], action["data"])


class Delete(Action):
    def __init__(self, name, data):
        super(Delete, self).__init__(name=name, data=data)

    @classmethod
    def action(cls, name, data):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name),
            "name": name,
            "data": copy.deepcopy(data),
        }

    def description(name):
        raise "not implemented"

    @classmethod
    def inverse(cls, action):
        return cls.inverseAction().action(action["name"], action["data"])


class Rename(Action):
    def __init__(self, oldName, newName):
        super(Rename, self).__init__(oldName=oldName, newName=newName)

    @classmethod
    def action(cls, oldName, newName):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(oldName, newName),
            "oldname": oldName,
            "newname": newName,
        }

    def description(oldName, newName):
        raise "not implemented"

    def do(data, updateDataFunction, saveFunctions, widgetFunction, action):
        updateDataFunction(action["oldname"], action["newname"])
        widgetFunction(action["oldname"], action["newname"])
        for child in list(data.keys()):
            if child.find(action["oldname"]) == 0 and child[len(action["oldname"]) :].startswith("/"):  # checks if item is a descendant of this entry
                newChildPath = action["newname"] + child[len(action["oldname"]) :]
                updateDataFunction(child, newChildPath)
                widgetFunction(child, newChildPath)
        for saveFunction in saveFunctions:
            saveFunction()

    @classmethod
    def inverse(cls, action):
        return cls.action(action["newname"], action["oldname"])


class ValueChange(Action):
    def __init__(self, name, valueName, oldValue, newValue):
        if oldValue == newValue:
            return
        super(ValueChange, self).__init__(name=name, valueName=valueName, oldValue=oldValue, newValue=newValue)

    @classmethod
    def action(cls, name, valueName, oldValue, newValue):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(name, valueName, oldValue, newValue),
            "name": name,
            "valuename": valueName,
            "oldvalue": oldValue,
            "newvalue": newValue,
        }

    def description(name, valueName, oldValue, newValue):
        raise "not implemented"

    @classmethod
    def inverse(cls, action):
        return cls.action(action["name"], action["valuename"], action["newvalue"], action["oldvalue"])
