import gui.crate.Config as Config
import gui.crate.LabSetup as LabSetup
import gui.crate.MultiRun as MultiRun
import gui.crate.RPC as RPC
import gui.crate.Sequences as Sequences
import gui.crate.Variables as Variables
import gui.widgets.History as History

gui = None
labsetup = None
sequences = None
variables = None
multiruns = None
rpcs = None
config = None
device_db = None
core_addr = None
loadDone = False

undoStack = []
redoStack = []


ACTION_TYPES = {
    "labsetup": {
        "add": LabSetup.Add,
        "delete": LabSetup.Delete,
        "rename": LabSetup.Rename,
        "valuechange": LabSetup.ValueChange,
    },
    "variables": {
        "add": Variables.Add,
        "delete": Variables.Delete,
        "rename": Variables.Rename,
        "valuechange": Variables.ValueChange,
    },
    "rpc": {
        "add": RPC.Add,
        "delete": RPC.Delete,
        "rename": RPC.Rename,
        "valuechange": RPC.ValueChange,
        "scriptchange": RPC.ScriptChange,
    },
    "multirun": {
        "add": MultiRun.Add,
        "delete": MultiRun.Delete,
        "rename": MultiRun.Rename,
        "valuechange": MultiRun.ValueChange,
        "dimensionadd": MultiRun.DimensionAdd,
        "dimensiondelete": MultiRun.DimensionDelete,
        "dimensionvaluechange": MultiRun.DimensionValueChange,
        "variableadd": MultiRun.VariableAdd,
        "variabledelete": MultiRun.VariableDelete,
        "variablevaluechange": MultiRun.VariableValueChange,
    },
    "sequences": {
        "add": Sequences.Add,
        "delete": Sequences.Delete,
        "rename": Sequences.Rename,
        "valuechange": Sequences.ValueChange,
        "segmentadd": Sequences.SegmentAdd,
        "segmentdelete": Sequences.SegmentDelete,
        "segmentindexchange": Sequences.SegmentIndexChange,
        "segmentvaluechange": Sequences.SegmentValueChange,
        "portstateadd": Sequences.PortStateAdd,
        "portstatedelete": Sequences.PortStateDelete,
        "portstatevaluechange": Sequences.PortStateValueChange,
        "rpcadd": Sequences.RPCAdd,
        "rpcdelete": Sequences.RPCDelete,
        "rpcvaluechange": Sequences.RPCValueChange,
    },
    "config": {
        "valuechange": Config.ValueChange,
    },
}


def executeAction(action):
    ACTION_TYPES[action["target"]][action["type"]].do(action)


def inverseAction(action):
    return ACTION_TYPES[action["target"]][action["type"]].inverse(action)


def loadDeviceDbVariables(deviceDbData):
    exec(deviceDbData, globals())


def undo():
    if len(undoStack) > 0:
        action = undoStack.pop()
        redoStack.append(action)
        updateHistoryText()
        executeAction(inverseAction(action))
    for window in gui.windows:
        window.undoAction.setEnabled(len(undoStack) > 0)
        window.redoAction.setEnabled(True)


def redo():
    if len(redoStack) > 0:
        action = redoStack.pop()
        undoStack.append(action)
        updateHistoryText()
        executeAction(action)
    for window in gui.windows:
        window.undoAction.setEnabled(True)
        window.redoAction.setEnabled(len(redoStack) > 0)


def appendToUndoStack(action):
    undoStack.append(action)
    redoStack.clear()
    for window in gui.windows:
        window.undoAction.setEnabled(True)
        window.redoAction.setEnabled(False)
    updateHistoryText()


def updateHistoryText():
    History.updateText(undoStack, redoStack)
