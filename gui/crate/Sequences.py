import copy

import gui.crate as crate
import gui.crate.FileManager
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.SequenceEditor
import gui.widgets.Variables as Variables

DEFAULT_SEQUENCE_VALUES = {
    "segments": {},
    "appearances": {},
    "pre_compile_rpc": None,
    "pre_compile_args": "",
}


DEFAULT_PORTSTATE_VALUES = {}
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.ttl"] = {
    "state": True,
}
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.zotino"] = {
    "voltage": {"text": "100", "unit": {"text": "mV", "factor": 1e-3}},
    "sweep_enable": False,
    "sweep_voltage": {"text": "200", "unit": {"text": "mV", "factor": 1e-3}},
    "formula_enable": False,
    "formula_name": "Lin | linear",
    "formula_text": "x",
    "formula_scale_factor": {"scaleX" : 1, "scaleY" : 1, "offsetY" : 0},
    "loadData_enable": False,
    "loaded_dataset": {"x": [1, 2, 3], "y": [2, 3, 5], "importDataFileName": "None"},
    "dataset_unit_time": {"text": "us", "factor": 1e-6},
    "dataset_unit_voltage": {"text": "mV", "factor": 1e-3},
}
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.fastino"] = {}
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.fastino"].update(copy.deepcopy(DEFAULT_PORTSTATE_VALUES["artiq.coredevice.zotino"]))
DEFAULT_PORTSTATE_VALUES["custom.CurrentDriver"] = {}
DEFAULT_PORTSTATE_VALUES["custom.CurrentDriver"].update(copy.deepcopy(DEFAULT_PORTSTATE_VALUES["artiq.coredevice.zotino"]))
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.sampler"] = {
    "freq": {"text": "10", "unit": {"text": "kHz", "factor": 1e3}},
}
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.ad9910"] = {
    "switch_enable": True,
    "switch": True,
    "attenuation_enable": False,
    "attenuation": {"text": "10", "unit": {"text": "dB", "factor": 1}},
    "mode": "Normal",
    "mode_enable": True,
    "freq": {"text": "100", "unit": {"text": "MHz", "factor": 1e6}},
    "amp": "1.0",
    "phase": "0.0",
    "sweep_freq": {"text": "200", "unit": {"text": "MHz", "factor": 1e6}},
    "sweep_amp": "0.5",
    "sweep_duration_enable": False,
    "sweep_duration": {"text": "10", "unit": {"text": "ms", "factor": 1e-3}},
    "ram_phase_formula": "0.0",
    "ram_phase_formula_name": "None",
    "ram_amplitude_formula": "1.0",
    "ram_amplitude_formula_name": "None",
    "ram_frequency_formula": "1e6",
    "ram_frequency_formula_name": "None",
    "ram_profile": "1",
    "ram_start": "0",
    "ram_end": "1023",
    "ram_step_size": "16",
    "ram_destination": "RAM_DEST_POWASF",
    "ram_mode": "RAM_MODE_RAMPUP",
}
DEFAULT_PORTSTATE_VALUES["artiq.coredevice.adf5356"] = {
    "switch_enable": True,
    "freq_enable": True,
    "attenuation_enable": False,
    "switch": True,
    "freq": {"text": "1000", "unit": {"text": "MHz", "factor": 1e6}},
    "attenuation": {"text": "10", "unit": {"text": "dB", "factor": 1}},
    "skipInit": False,
    "useAlmazny": False,
}

DEFAULT_SEGMENT_VALUES = {
    "enabled": True,
    "duration": {"text": "10", "unit": {"text": "ms", "factor": 1e-3}},
    "description": "",
    "repeats": "1",
    "subsequence": None,
    "input_ttl": None,
}

DEFAULT_RPC_VALUES = {
    "args": "",
    "kargs": {},
}


def updateSubsequenceAppearancesInDict(d, seqName, segName, oldValue, newValue):
    if oldValue is not None and oldValue != "":
        if segName in d[oldValue]["appearances"][seqName]:
            d[oldValue]["appearances"][seqName].remove(segName)
        if len(d[oldValue]["appearances"][seqName]) == 0:
            d[oldValue]["appearances"].pop(seqName)
    if newValue is not None and newValue != "":
        if seqName not in d[newValue]["appearances"]:
            d[newValue]["appearances"][seqName] = []
        if segName not in d[newValue]["appearances"][seqName]:
            d[newValue]["appearances"][seqName].append(segName)


def getSequenceValue(seqName, valueName):
    if valueName not in crate.sequences[seqName]:
        crate.sequences[seqName][valueName] = copy.deepcopy(DEFAULT_SEQUENCE_VALUES[valueName])
    return crate.sequences[seqName][valueName]


def getPortStateValue(seqName, segName, portName, valueName):
    portState = crate.sequences[seqName]["segments"][segName]["ports"][portName]
    if valueName not in portState:
        module = crate.labsetup[portName]["module"]
        portState[valueName] = copy.deepcopy(DEFAULT_PORTSTATE_VALUES[module][valueName])
    return portState[valueName]


def getRPCValue(seqName, segName, rpcName, valueName):
    rpc = crate.sequences[seqName]["segments"][segName]["rpcs"][rpcName]
    if valueName not in rpc:
        rpc[valueName] = copy.deepcopy(DEFAULT_RPC_VALUES[valueName])
    return rpc[valueName]


class Add(crate.Actions.Add):
    def __init__(self, seqName, seqData):
        if "appearances" not in seqData:
            seqData["appearances"] = {}
        if "segments" not in seqData:
            seqData["segments"] = {}
        super(Add, self).__init__(seqName, seqData)

    def description(seqName):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} added"

    def do(action):
        crate.sequences[action["name"]] = action["data"]
        if not action["data"]["isDir"]:
            for segName, segData in action["data"]["segments"].items():
                if segData["type"] == "subsequence":
                    updateSubsequenceAppearancesInDict(
                        crate.sequences,
                        action["name"],
                        segName,
                        None,
                        segData["subsequence"],
                    )
        gui.crate.FileManager.saveSequences()
        gui.widgets.SequenceEditor.dock.addItem(action["name"], isDir=action["data"]["isDir"])

    def inverseAction():
        return Delete


class Delete(crate.Actions.Delete):
    def __init__(self, seqName):
        # check if this sequence still appears as subsequence in other sequences
        if not crate.sequences[seqName]["isDir"]:
            for appearedSeq in crate.sequences[seqName]["appearances"]:
                Design.errorDialog(
                    "Error",
                    f"Sequence {seqName} is still used as subsequence in {appearedSeq}.",
                )
                return
        super(Delete, self).__init__(seqName, crate.sequences[seqName])

    def description(seqName):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} deleted"

    def do(action):
        if not crate.sequences[action["name"]]["isDir"]:
            crate.sequences[action["name"]] = action["data"]
            for segName, segData in action["data"]["segments"].items():
                if segData["type"] == "subsequence":
                    updateSubsequenceAppearancesInDict(
                        crate.sequences,
                        action["name"],
                        segName,
                        segData["subsequence"],
                        None,
                    )
        crate.sequences.pop(action["name"])
        gui.crate.FileManager.saveSequences()
        gui.widgets.SequenceEditor.dock.deleteItem(action["name"])

    def inverseAction():
        return Add


class Rename(crate.Actions.Rename):
    def __init__(self, oldName, newName):
        super(Rename, self).__init__(oldName, newName)

    def description(oldName, newName):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {oldName} renamed to {newName}"

    def do(action):
        crate.Actions.Rename.do(
            crate.sequences,
            Rename.updateData,
            [gui.crate.FileManager.saveSequences],
            gui.widgets.SequenceEditor.dock.renameItem,
            action,
        )

    def updateData(oldName, newName):
        crate.sequences[newName] = crate.sequences.pop(oldName)

        # check all occurences of subsequences in other sequences
        for seqData in crate.sequences.values():
            if seqData["isDir"]:
                continue
            for segData in seqData["segments"].values():
                if segData["type"] == "subsequence" and segData["subsequence"] == oldName:
                    segData["subsequence"] = newName
            if oldName in seqData["appearances"]:
                seqData["appearances"][newName] = seqData["appearances"].pop(oldName)
        
        # check if its the currently selected sequence
        if gui.widgets.SequenceEditor.dock.list.currentSelection == oldName:
            gui.widgets.SequenceEditor.dock.list.currentSelection = newName


class ValueChange(crate.Actions.ValueChange):
    def __init__(self, seqName, valueName, newValue):
        super(ValueChange, self).__init__(seqName, valueName, crate.sequences[seqName][valueName], newValue)

    def description(seqName, valueName, oldValue, newValue):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName}: Changed {valueName} from {oldValue} to {newValue}"

    def do(action):
        crate.sequences[action["name"]][action["valuename"]] = action["newvalue"]
        gui.crate.FileManager.saveSequences()


class SegmentAdd(crate.Actions.Action):
    def __init__(self, seqName, segName=None, segData=None, index=None):
        if segName is None:
            segName = util.getUniqueKey(crate.sequences[seqName]["segments"], "segment")
        if segData is None:
            segData = {"type": "portstate"}
        if "description" not in segData:
            segData["description"] = "Port State" if segData["type"] == "portstate" else segData["type"].capitalize()
        if segData["type"] == "portstate" and "ports" not in segData:
            segData["ports"] = {}
        if segData["type"] == "portstate" and "rpcs" not in segData:
            segData["rpcs"] = {}
        if index is None:
            index = len(crate.sequences[seqName]["segments"])
        elif index < 0:
            index = len(crate.sequences[seqName]["segments"]) + 1 + index
        super(SegmentAdd, self).__init__(seqName=seqName, segName=segName, segData=segData, index=index)

    @classmethod
    def action(cls, seqName, segName, segData, index):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segData, index),
            "seqname": seqName,
            "segname": segName,
            "segdata": copy.deepcopy(segData),
            "index": index,
        }

    def description(seqName, segData, index):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName}: Added Segment in Pos {index}"

    def do(action):
        seqData = crate.sequences[action["seqname"]]
        seqData["segments"][action["segname"]] = action["segdata"]
        seqData["segments"] = util.setIndexOfKeyInDict(seqData["segments"], action["segname"], action["index"])
        if action["segdata"]["type"] == "subsequence" and "subsequence" in action["segdata"]:
            updateSubsequenceAppearancesInDict(
                crate.sequences,
                action["seqname"],
                action["segname"],
                None,
                action["segdata"]["subsequence"],
            )
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.addNewSegment(action["segname"], action["segdata"], action["index"])

    def inverse(action):
        return SegmentDelete.action(action["seqname"], action["segname"], action["segdata"], action["index"])


class SegmentDelete(crate.Actions.Action):
    def __init__(self, seqName, segName):
        segData = crate.sequences[seqName]["segments"][segName]
        index = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        super(SegmentDelete, self).__init__(seqName=seqName, segName=segName, segData=segData, index=index)

    @classmethod
    def action(cls, seqName, segName, segData, index):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segData, index),
            "seqname": seqName,
            "segname": segName,
            "segdata": copy.deepcopy(segData),
            "index": index,
        }

    def description(seqName, segData, index):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName}: Deleted Segment in Pos {index}"

    def do(action):
        crate.sequences[action["seqname"]]["segments"].pop(action["segname"])
        if action["segdata"]["type"] == "subsequence":
            updateSubsequenceAppearancesInDict(
                crate.sequences,
                action["seqname"],
                action["segname"],
                action["segdata"]["subsequence"],
                None,
            )
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.deleteSegment(action["segname"])

    def inverse(action):
        return SegmentAdd.action(action["seqname"], action["segname"], action["segdata"], action["index"])


class SegmentIndexChange(crate.Actions.Action):
    def __init__(self, seqName, segName, oldIndex, newIndex):
        super(SegmentIndexChange, self).__init__(seqName=seqName, segName=segName, oldIndex=oldIndex, newIndex=newIndex)

    @classmethod
    def action(cls, seqName, segName, oldIndex, newIndex):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, oldIndex, newIndex),
            "seqname": seqName,
            "segname": segName,
            "oldindex": oldIndex,
            "newindex": newIndex,
        }

    def description(seqName, oldIndex, newIndex):
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName}: Pos {oldIndex} moved to {newIndex}."

    def do(action):
        seqData = crate.sequences[action["seqname"]]
        seqData["segments"] = util.setIndexOfKeyInDict(seqData["segments"], action["segname"], action["newindex"])
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.segmentIndexChanged(action["segname"], action["newindex"])

    def inverse(action):
        return SegmentIndexChange.action(action["seqname"], action["segname"], action["newindex"], action["oldindex"])


def segmentGet(seqName, segName, valueName):
    segment = crate.sequences[seqName]["segments"][segName]
    if valueName not in segment:
        segment[valueName] = copy.deepcopy(DEFAULT_SEGMENT_VALUES[valueName])
    return segment[valueName]


class SegmentValueChange(crate.Actions.Action):
    def __init__(self, seqName, segName, valueName, newValue):
        oldValue = crate.sequences[seqName]["segments"][segName][valueName]
        if oldValue == newValue:
            return
        super(SegmentValueChange, self).__init__(
            seqName=seqName,
            segName=segName,
            valueName=valueName,
            oldValue=oldValue,
            newValue=newValue,
        )

    @classmethod
    def action(
        cls,
        seqName,
        segName,
        valueName,
        oldValue,
        newValue,
        sequenceNameStack=None,
        sequencesCopy=None,
    ):
        action = {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(
                seqName,
                segName,
                valueName,
                oldValue,
                newValue,
                sequencesCopy=sequencesCopy,
            ),
            "seqname": seqName,
            "segname": segName,
            "valuename": valueName,
            "newvalue": newValue,
            "oldvalue": oldValue,
            "preactions": [],
            "postactions": [],
        }
        if valueName == "subsequence":
            if sequencesCopy is None:
                sequencesCopy = copy.deepcopy(crate.sequences)
            updateSubsequenceAppearancesInDict(sequencesCopy, seqName, segName, oldValue, newValue)
            sequencesCopy[seqName]["segments"][segName]["subsequence"] = newValue
            oldDuration = sequencesCopy[seqName]["segments"][segName]["duration"]
            newDuration = SegmentValueChange.getSubsequenceDuration(sequencesCopy, seqName, segName)
            action["postactions"].append(
                SegmentValueChange.action(
                    seqName,
                    segName,
                    "duration",
                    oldDuration,
                    newDuration,
                    sequencesCopy=sequencesCopy,
                    sequenceNameStack=[newValue],
                )
            )
        elif valueName == "repeats":
            if sequencesCopy is None:
                sequencesCopy = copy.deepcopy(crate.sequences)
            sequencesCopy[seqName]["segments"][segName]["repeats"] = newValue
            oldDuration = sequencesCopy[seqName]["segments"][segName]["duration"]
            newDuration = SegmentValueChange.getSubsequenceDuration(sequencesCopy, seqName, segName)
            action["postactions"].append(
                SegmentValueChange.action(
                    seqName,
                    segName,
                    "duration",
                    oldDuration,
                    newDuration,
                    sequencesCopy=sequencesCopy,
                )
            )
        elif valueName == "duration":
            if sequencesCopy is None:
                sequencesCopy = copy.deepcopy(crate.sequences)
            if sequenceNameStack is not None:
                if seqName in sequenceNameStack:
                    newValue = {"text": "inf", "unit": {"text": "ms", "factor": 1e-3}}
                    action["newvalue"] = newValue
                else:
                    sequenceNameStack.append(seqName)
            else:
                sequenceNameStack = [seqName]
            if sequencesCopy[seqName]["segments"][segName]["duration"] != newValue:
                sequencesCopy[seqName]["segments"][segName]["duration"] = newValue
                for appearanceSeqName, appearanceSegNames in sequencesCopy[seqName]["appearances"].items():
                    for appearanceSegName in appearanceSegNames:
                        if sequencesCopy[appearanceSeqName]["segments"][appearanceSegName]["type"] != "subsequence":
                            continue
                        oldSeqDuration = sequencesCopy[appearanceSeqName]["segments"][appearanceSegName]["duration"]
                        newSeqDuration = SegmentValueChange.getSubsequenceDuration(sequencesCopy, appearanceSeqName, appearanceSegName)
                        action["postactions"].append(
                            SegmentValueChange.action(
                                appearanceSeqName,
                                appearanceSegName,
                                "duration",
                                oldSeqDuration,
                                newSeqDuration,
                                sequenceNameStack=sequenceNameStack.copy(),
                                sequencesCopy=sequencesCopy,
                            )
                        )
        return action

    def getSubsequenceDuration(d, seqName, segName):
        subsequence = d[seqName]["segments"][segName]["subsequence"]
        newDuration = 0
        if subsequence in d:
            for segData in d[subsequence]["segments"].values():
                newDuration += Input.getValueFromState(segData["duration"], reader=float, replacer=Variables.replacer)
            repeats = d[seqName]["segments"][segName]["repeats"]
            repeatsValue = Input.getValueFromState(repeats, reader=float, replacer=Variables.replacer)
            newDuration *= repeatsValue
        if newDuration > 1:
            return {"text": str(newDuration), "unit": {"text": "s", "factor": 1}}
        elif newDuration > 1e-3 or newDuration == 0:
            return {
                "text": str(newDuration * 1e3),
                "unit": {"text": "ms", "factor": 1e-3},
            }
        else:
            return {
                "text": str(newDuration * 1e6),
                "unit": {"text": "us", "factor": 1e-6},
            }

    def description(seqName, segName, valueName, oldValue, newValue, sequencesCopy=None):
        if type(oldValue) is dict and "text" in oldValue and "unit" in oldValue:
            oldValue = util.unitValueToText(oldValue)
            newValue = util.unitValueToText(newValue)
        if sequencesCopy is None:
            sequencesCopy = crate.sequences
        segIndex = list(sequencesCopy[seqName]["segments"].keys()).index(segName)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: Changed {valueName} from {oldValue} to {newValue}."

    def do(action):
        for preAction in action["preactions"]:
            crate.executeAction(preAction)
        crate.sequences[action["seqname"]]["segments"][action["segname"]][action["valuename"]] = action["newvalue"]
        if action["valuename"] == "subsequence":
            updateSubsequenceAppearancesInDict(
                crate.sequences,
                action["seqname"],
                action["segname"],
                action["oldvalue"],
                action["newvalue"],
            )
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).segmentValueChange(action["valuename"], action["newvalue"])
        for postAction in action["postactions"]:
            crate.executeAction(postAction)

    def inverse(action):
        action = copy.deepcopy(action)
        action["newvalue"], action["oldvalue"] = action["oldvalue"], action["newvalue"]
        crate.Actions.inversePrePostActions(action)
        action["description"] = SegmentValueChange.description(
            action["seqname"],
            action["segname"],
            action["valuename"],
            action["oldvalue"],
            action["newvalue"],
        )
        return action


class PortStateAdd(crate.Actions.Action):
    def __init__(self, seqName, segName, portName, portData=None):
        if portData is None:
            portData = {}
        super(PortStateAdd, self).__init__(seqName=seqName, segName=segName, portName=portName, portData=portData)

    @classmethod
    def action(cls, seqName, segName, portName, portData):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segName, portName),
            "seqname": seqName,
            "segname": segName,
            "portname": portName,
            "portdata": copy.deepcopy(portData),
        }

    def description(seqName, segName, portName):
        segIndex = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: Added PortState {portName}"

    def do(action):
        crate.sequences[action["seqname"]]["segments"][action["segname"]]["ports"][action["portname"]] = action["portdata"]
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).addPortState(action["portname"])

    def inverse(action):
        return PortStateDelete.action(action["seqname"], action["segname"], action["portname"], action["portdata"])


class PortStateDelete(crate.Actions.Action):
    def __init__(self, seqName, segName, portName):
        portData = crate.sequences[seqName]["segments"][segName]["ports"][portName]
        super(PortStateDelete, self).__init__(seqName=seqName, segName=segName, portName=portName, portData=portData)

    @classmethod
    def action(cls, seqName, segName, portName, portData):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segName, portName),
            "seqname": seqName,
            "segname": segName,
            "portname": portName,
            "portdata": copy.deepcopy(portData),
        }

    def description(seqName, segName, portName):
        segIndex = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: Deleted PortState {portName}"

    def do(action):
        crate.sequences[action["seqname"]]["segments"][action["segname"]]["ports"].pop(action["portname"])
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).deletePortState(action["portname"])

    def inverse(action):
        return PortStateAdd.action(action["seqname"], action["segname"], action["portname"], action["portdata"])


class PortStateValueChange(crate.Actions.Action):
    def __init__(self, seqName, segName, portName, valueName, newValue):
        oldValue = crate.sequences[seqName]["segments"][segName]["ports"][portName][valueName]
        if oldValue == newValue:
            return
        super(PortStateValueChange, self).__init__(
            seqName=seqName,
            segName=segName,
            portName=portName,
            valueName=valueName,
            oldValue=oldValue,
            newValue=newValue,
        )

    @classmethod
    def action(cls, seqName, segName, portName, valueName, oldValue, newValue):
        action = {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segName, portName, valueName, oldValue, newValue),
            "seqname": seqName,
            "segname": segName,
            "portname": portName,
            "valuename": valueName,
            "newvalue": newValue,
            "oldvalue": oldValue,
            "preactions": [],
            "postactions": [],
        }
        return action

    def description(seqName, segName, portName, valueName, oldValue, newValue):
        segIndex = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        if type(oldValue) is dict and "text" in oldValue and "unit" in oldValue:
            oldValue = util.unitValueToText(oldValue)
            newValue = util.unitValueToText(newValue)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: PortState {portName}: Changed {valueName} from {oldValue} to {newValue}"

    def do(action):
        for preaction in action["preactions"]:
            crate.executeAction(preaction)
        crate.sequences[action["seqname"]]["segments"][action["segname"]]["ports"][action["portname"]][action["valuename"]] = action["newvalue"]
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).getPortState(action["portname"]).valueChange(action["valuename"], action["newvalue"])
        for postaction in action["postactions"]:
            crate.executeAction(postaction)

    def inverse(action):
        action = copy.deepcopy(action)
        action["newvalue"], action["oldvalue"] = action["oldvalue"], action["newvalue"]
        crate.Actions.inversePrePostActions(action)
        action["description"] = PortStateValueChange.description(
            action["seqname"],
            action["segname"],
            action["portname"],
            action["valuename"],
            action["oldvalue"],
            action["newvalue"],
        )
        return action


class RPCAdd(crate.Actions.Action):
    def __init__(self, seqName, segName, rpcName, rpcData=None):
        if rpcData is None:
            rpcData = {}
        super(RPCAdd, self).__init__(seqName=seqName, segName=segName, rpcName=rpcName, rpcData=rpcData)

    @classmethod
    def action(cls, seqName, segName, rpcName, rpcData):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segName, rpcName),
            "seqname": seqName,
            "segname": segName,
            "rpcname": rpcName,
            "rpcdata": copy.deepcopy(rpcData),
        }

    def description(seqName, segName, rpcName):
        segIndex = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: Added RPC {rpcName}"

    def do(action):
        crate.sequences[action["seqname"]]["segments"][action["segname"]]["rpcs"][action["rpcname"]] = action["rpcdata"]
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).addRPC(action["rpcname"])

    def inverse(action):
        return RPCDelete.action(action["seqname"], action["segname"], action["rpcname"], action["rpcdata"])


class RPCDelete(crate.Actions.Action):
    def __init__(self, seqName, segName, rpcName):
        rpcData = crate.sequences[seqName]["segments"][segName]["rpcs"][rpcName]
        super(RPCDelete, self).__init__(seqName=seqName, segName=segName, rpcName=rpcName, rpcData=rpcData)

    @classmethod
    def action(cls, seqName, segName, rpcName, rpcData):
        return {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segName, rpcName),
            "seqname": seqName,
            "segname": segName,
            "rpcname": rpcName,
            "rpcdata": copy.deepcopy(rpcData),
        }

    def description(seqName, segName, rpcName):
        segIndex = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: Deleted RPC {rpcName}"

    def do(action):
        crate.sequences[action["seqname"]]["segments"][action["segname"]]["rpcs"].pop(action["rpcname"])
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).deleteRPC(action["rpcname"])

    def inverse(action):
        return RPCAdd.action(action["seqname"], action["segname"], action["rpcname"], action["rpcdata"])


class RPCValueChange(crate.Actions.Action):
    def __init__(self, seqName, segName, rpcName, valueName, newValue):
        oldValue = crate.sequences[seqName]["segments"][segName]["rpcs"][rpcName][valueName]
        if oldValue == newValue:
            return
        super(RPCValueChange, self).__init__(
            seqName=seqName,
            segName=segName,
            rpcName=rpcName,
            valueName=valueName,
            oldValue=oldValue,
            newValue=newValue,
        )

    @classmethod
    def action(cls, seqName, segName, rpcName, valueName, oldValue, newValue):
        action = {
            "target": cls.__module__.split(".")[-1].lower(),
            "type": cls.__name__.lower(),
            "description": cls.description(seqName, segName, rpcName, valueName, oldValue, newValue),
            "seqname": seqName,
            "segname": segName,
            "rpcname": rpcName,
            "valuename": valueName,
            "newvalue": newValue,
            "oldvalue": oldValue,
            "preactions": [],
            "postactions": [],
        }
        return action

    def description(seqName, segName, rpcName, valueName, oldValue, newValue):
        segIndex = list(crate.sequences[seqName]["segments"].keys()).index(segName)
        if type(oldValue) is dict and "text" in oldValue and "unit" in oldValue:
            oldValue = util.unitValueToText(oldValue)
            newValue = util.unitValueToText(newValue)
        return f"{gui.widgets.SequenceEditor.title}: Sequence {seqName} Pos {segIndex}: RPC {rpcName}: Changed {valueName} from {oldValue} to {newValue}"

    def do(action):
        for preaction in action["preactions"]:
            crate.executeAction(preaction)
        crate.sequences[action["seqname"]]["segments"][action["segname"]]["rpcs"][action["rpcname"]][action["valuename"]] = action["newvalue"]
        gui.crate.FileManager.saveSequences()
        if gui.widgets.SequenceEditor.dock.configWidget.name == action["seqname"]:
            gui.widgets.SequenceEditor.dock.configWidget.getSegment(action["segname"]).getRPC(action["rpcname"]).valueChange(action["valuename"], action["newvalue"])
        for postaction in action["postactions"]:
            crate.executeAction(postaction)

    def inverse(action):
        action = copy.deepcopy(action)
        action["newvalue"], action["oldvalue"] = action["oldvalue"], action["newvalue"]
        crate.Actions.inversePrePostActions(action)
        action["description"] = RPCValueChange.description(
            action["seqname"],
            action["segname"],
            action["rpcname"],
            action["valuename"],
            action["oldvalue"],
            action["newvalue"],
        )
        return action
