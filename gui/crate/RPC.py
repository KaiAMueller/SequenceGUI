import copy
import os

import gui.crate as crate
import gui.crate.Actions as Actions
import gui.crate.FileManager as FileManager
import gui.widgets.Design as Design
import gui.widgets.RPC
import gui.widgets.Segment
import gui.widgets.SequenceEditor

DEFAULT_SCRIPT = """
# Available Variables:
#   - args: list of strings
#   - kargs: key-value pairs as dictionary (keys and values are always strings)
#   - runVariables: deep copy of variable dictionary defined by the Variable widget or set by the Multi Run at compile time
#   - exitFlag: Use exitFlag.is_set() to check if the script should be stopped.
#   - print: prints to the GUI Log
# 
# About the Execution Mode:
#  - "normal": The script will be executed in the main thread of the GUI.
#    This means that the GUI will freeze while the script is running.
#    Executes fastest with low jitter.
#  - "thread": The script will be executed in a separate thread.
#    Threads cannot be killed. Check the exitFlag in your code to stop it.
#    Around 1 ms slower and may have slightly more jitter than normal mode.
#  - "subprocess": The script will be executed in a seperate process.
#    Processes can be killed by the GUI or using exitFlag.
#    Super slow execution delay (~1000 ms) and huge jitter.

print(args)
print(kargs)
"""

DEFAULT_VALUES = {"mode": "normal"}


def getValue(rpcName, valueName):
    if valueName not in crate.rpcs[rpcName]:
        if valueName == "file":
            crate.rpcs[rpcName][valueName] = rpcName + ".py"
        else:
            crate.rpcs[rpcName][valueName] = copy.deepcopy(DEFAULT_VALUES[valueName])
    return crate.rpcs[rpcName][valueName]


def getScript(rpcName):
    path = FileManager.getScriptsPath() + getValue(rpcName, "file")
    if not os.path.isfile(path):
        file = open(path, "w")
        file.write(DEFAULT_SCRIPT)
        file.close()

    file = open(path, "r")
    script = file.read()
    file.close()
    return script


class Add(Actions.Add):
    def __init__(self, rpcName, rpcData):
        super(Add, self).__init__(rpcName, rpcData)

    def description(rpcName):
        return f"{gui.widgets.RPC.title}: RPC {rpcName} added"

    def do(action):
        crate.rpcs[action["name"]] = action["data"]
        FileManager.saveRPC()
        gui.widgets.RPC.dock.addItem(action["name"], isDir=action["data"]["isDir"])
        if gui.widgets.SequenceEditor.dock.configWidget is not None:
            for segment in gui.widgets.SequenceEditor.dock.configWidget.segments():
                if type(segment) is gui.widgets.Segment.PortStates:
                    segment.addRPCSpacer(action["name"])

    def inverseAction():
        return Delete


class Delete(Actions.Delete):
    def __init__(self, rpcName):
        # check if rpc is still used in any sequence
        for seqName, seqData in crate.sequences.items():
            if seqData["isDir"]:
                continue
            for segName, segData in seqData["segments"].items():
                if segData["type"] == "portstate":
                    for rpcName2, rpcData in segData["rpcs"].items():
                        if rpcName2 == rpcName:
                            Design.errorDialog(
                                "Error",
                                f'RPC "{rpcName}" is still used in sequence "{seqName}".',
                            )
                            return
        super(Delete, self).__init__(rpcName, crate.rpcs[rpcName])

    def description(rpcName):
        return f"{gui.widgets.RPC.title}: RPC {rpcName} deleted"

    def do(action):
        crate.rpcs.pop(action["name"])
        FileManager.saveRPC()
        gui.widgets.RPC.dock.deleteItem(action["name"])

    def inverseAction():
        return Add


class Rename(Actions.Rename):
    def __init__(self, oldName, newName):
        super(Rename, self).__init__(oldName, newName)

    def description(oldName, newName):
        return f"{gui.widgets.RPC.title}: RPC {oldName} renamed to {newName}"

    def do(action):
        Actions.Rename.do(
            crate.rpcs,
            Rename.updateData,
            [FileManager.saveRPC, FileManager.saveSequences],
            gui.widgets.RPC.dock.renameItem,
            action,
        )

    def updateData(oldName, newName):
        crate.rpcs[newName] = crate.rpcs.pop(oldName)

        # find all sequences that use the rpc
        for seqName, seqData in crate.sequences.items():
            for segName, segData in seqData["segments"].items():
                if segData["type"] == "portstate":
                    if oldName in segData["rpcs"]:
                        segData["rpcs"][newName] = segData["rpcs"].pop(oldName)
                        if gui.widgets.SequenceEditor.dock.configWidget is not None:
                            if seqName == gui.widgets.SequenceEditor.dock.configWidget.name:
                                gui.widgets.SequenceEditor.dock.configWidget.getSegment(segName).renameRPC(oldName, newName)


class ValueChange(Actions.ValueChange):
    def __init__(self, rpcName, valueName, newValue):
        oldValue = crate.rpcs[rpcName][valueName]
        if oldValue == newValue:
            return
        super(ValueChange, self).__init__(rpcName, valueName, oldValue, newValue)

    def description(rpcName, valueName, oldValue, newValue):
        return f"{gui.widgets.RPC.title}: RPC {rpcName}: Changed {valueName} from {oldValue} to {newValue}"

    def do(action):
        crate.rpcs[action["name"]][action["valuename"]] = action["newvalue"]
        FileManager.saveRPC()
        gui.widgets.RPC.dock.widgetValueChange(action["name"], action["valuename"], action["newvalue"])


class ScriptChange(Actions.Action):
    def __init__(self, rpcName, oldScript, newScript):
        if oldScript is None:
            oldScript = getScript(rpcName)
        if oldScript == newScript:
            return
        super(ScriptChange, self).__init__(rpcName=rpcName, oldScript=oldScript, newScript=newScript)

    @classmethod
    def action(cls, rpcName, oldScript, newScript):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(rpcName),
            "rpcName": rpcName,
            "oldScript": oldScript,
            "newScript": newScript,
        }

    def description(rpcName):
        return f"{gui.widgets.RPC.title}: RPC {rpcName} script changed"

    @classmethod
    def inverse(cls, action):
        return ScriptChange.action(action["rpcName"], action["newScript"], action["oldScript"])

    def do(action):
        fileName = crate.rpcs[action["rpcName"]]["file"]
        path = FileManager.getScriptsPath() + fileName
        file = open(path, "w")
        file.write(action["newScript"])
        file.close()
        gui.widgets.RPC.dock.widgetValueChange(action["rpcName"], "script", action["newScript"])
