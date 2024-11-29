import copy

import gui.crate as crate
import gui.crate.Actions as Actions
import gui.crate.FileManager as FileManager
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.LabSetup
import gui.widgets.Segment
import gui.widgets.SequenceEditor

DEFAULT_VALUES = {}
DEFAULT_VALUES["artiq.coredevice.ttl"] = {
    "inverted": False,
}
DEFAULT_VALUES["artiq.coredevice.zotino"] = {
    "channel": "0",
    "calibration_enabled": False,
    "calibration_mode": "Formula",
    "calibration_formula": "x",
    "calibration_dataset": None,
    "calibration_unit_text": "nT",
    "calibration_to_unit": {"text": "mV", "factor": 1e-3},
}
DEFAULT_VALUES["artiq.coredevice.fastino"] = {}
DEFAULT_VALUES["artiq.coredevice.fastino"].update(copy.deepcopy(DEFAULT_VALUES["artiq.coredevice.zotino"]))
DEFAULT_VALUES["custom.CurrentDriver"] = {}
DEFAULT_VALUES["custom.CurrentDriver"].update(copy.deepcopy(DEFAULT_VALUES["artiq.coredevice.zotino"]))
DEFAULT_VALUES["custom.CurrentDriver"]["calibration_unit_text"] = "mA"
DEFAULT_VALUES["artiq.coredevice.sampler"] = {}
DEFAULT_VALUES["artiq.coredevice.ad9910"] = {}
DEFAULT_VALUES["artiq.coredevice.adf5356"] = {
    "hasAlmazny": False,
}


def get(portName, valueName):
    if valueName not in crate.labsetup[portName]:
        module = crate.labsetup[portName]["module"]
        crate.labsetup[portName][valueName] = copy.deepcopy(DEFAULT_VALUES[module][valueName])
    return crate.labsetup[portName][valueName]


class Add(Actions.Add):
    def __init__(self, portName, portData):
        super(Add, self).__init__(portName, portData)

    def description(portName):
        return f"{gui.widgets.LabSetup.title}: Port {portName} added"

    def do(action):
        crate.labsetup[action["name"]] = action["data"]
        FileManager.saveLabSetup()
        gui.widgets.LabSetup.dock.addItem(action["name"], isDir=action["data"]["isDir"])
        if gui.widgets.SequenceEditor.dock.configWidget is not None:
            for segment in gui.widgets.SequenceEditor.dock.configWidget.segments():
                if type(segment) is gui.widgets.Segment.PortStates:
                    segment.addPortStateSpacer(action["name"])

    def inverseAction():
        return Delete


class Delete(Actions.Delete):
    def __init__(self, portName):
        # check if port is still used in any sequence
        for seqName, seqData in crate.sequences.items():
            if seqData["isDir"]:
                continue
            for segName, segData in seqData["segments"].items():
                if segData["type"] == "portstate":
                    for portName2, portData in segData["ports"].items():
                        if portName2 == portName:
                            Design.errorDialog(
                                "Error",
                                f'Port "{portName}" is still used in sequence "{seqName}".',
                            )
                            return
        super(Delete, self).__init__(portName, crate.labsetup[portName])

    def description(portName):
        return f"{gui.widgets.LabSetup.title}: Port {portName} deleted"

    def do(action):
        crate.labsetup.pop(action["name"])
        FileManager.saveLabSetup()
        gui.widgets.LabSetup.dock.deletePort(action["name"])

    def inverseAction():
        return Add


class Rename(Actions.Rename):
    def __init__(self, oldName, newName):
        super(Rename, self).__init__(oldName, newName)

    def description(oldName, newName):
        return f"{gui.widgets.LabSetup.title}: Port {oldName} renamed to {newName}"

    def do(action):
        Actions.Rename.do(
            crate.labsetup,
            Rename.updateData,
            [FileManager.saveLabSetup, FileManager.saveSequences],
            gui.widgets.LabSetup.dock.renameItem,
            action,
        )

    def updateData(oldName, newName):
        crate.labsetup[newName] = crate.labsetup.pop(oldName)

        # find all sequences that use the port
        for seqName, seqData in crate.sequences.items():
            if seqData["isDir"]:
                continue
            for segName, segData in seqData["segments"].items():
                if segData["type"] == "portstate":
                    if oldName in segData["ports"]:
                        segData["ports"][newName] = segData["ports"].pop(oldName)
                        if gui.widgets.SequenceEditor.dock.configWidget is not None:
                            if seqName == gui.widgets.SequenceEditor.dock.configWidget.name:
                                gui.widgets.SequenceEditor.dock.configWidget.getSegment(segName).renamePortState(oldName, newName)


class ValueChange(Actions.ValueChange):
    def __init__(self, portName, valueName, newValue):
        oldValue = crate.labsetup[portName][valueName]
        if oldValue == newValue:
            return
        super(ValueChange, self).__init__(portName, valueName, oldValue, newValue)

    def description(portName, valueName, oldValue, newValue):
        if type(oldValue) is dict and "text" in oldValue and "unit" in oldValue:
            oldValue = util.unitValueToText(oldValue)
            newValue = util.unitValueToText(newValue)
        oldValueText = str(oldValue)
        newValueText = str(newValue)
        oldValueText = oldValueText if len(oldValueText) < 20 else oldValueText[:9] + "..." + oldValueText[-9:]
        newValueText = newValueText if len(newValueText) < 20 else newValueText[:9] + "..." + newValueText[-9:]
        return f"{gui.widgets.LabSetup.title}: Port {portName}: Changed {valueName} from {oldValueText} to {newValueText}"

    def do(action):
        crate.labsetup[action["name"]][action["valuename"]] = action["newvalue"]
        FileManager.saveLabSetup()
        gui.widgets.LabSetup.dock.widgetValueChange(action["name"], action["valuename"], action["newvalue"])
