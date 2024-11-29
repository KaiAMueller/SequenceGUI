import copy
import os
from datetime import datetime, timedelta

try:
    import sipyco.pc_rpc as rpc
except Exception:
    print("to install run 'pip install git+https://github.com/m-labs/sipyco'")
    raise Exception


import gui.code_generation.artiq_code_generator
import gui.crate as crate
import gui.settings as settings
import gui.util as util
import gui.widgets.Dataset as Dataset
import gui.widgets.Design as Design
import gui.widgets.Formula as Formula
import gui.widgets.Input as Input
import gui.widgets.MultiRun as MultiRun
import gui.widgets.Playlist as Playlist
import gui.widgets.RPC as RPC
import gui.widgets.Variables as Variables
from gui.widgets.Log import log


class TimeRunner:
    def __init__(self):
        self.time = 0

    def run(self, dt: float):
        oldTime = self.time
        self.time += dt
        return oldTime

    def reset(self):
        self.time = 0


def compileCode(seqName):
    compiledSeq = compileSequence(seqName, TimeRunner())
    if compiledSeq is None:
        raise Exception("cant compile because of looped subsequences")

    duration = compiledSeq[-1]["time"] + compiledSeq[-1]["duration"]
    codeID = int(datetime.now().strftime("%Y%m%d%H%M%S%f"))
    code = gui.code_generation.artiq_code_generator.generateCode(seqName, compiledSeq, codeID)
    return code, codeID, duration


def compileAndRun(seqName):
    pre_compile_rpc = crate.Sequences.getSequenceValue(seqName, "pre_compile_rpc")
    if pre_compile_rpc is not None:
        log(f"Running pre compile rpc {pre_compile_rpc} for sequence {seqName}")
        try:
            argtext = crate.Sequences.getSequenceValue(seqName, "pre_compile_args")
            tokens = argtext.strip().split(" ")
            args = []
            for arg in tokens:
                if arg == "":
                    continue
                args.append(Variables.replacer(arg))
            RPC.Server.run(RPC.Server(), pre_compile_rpc, *args)
        except Exception as e:
            log(e)

    try:
        compiledCode, codeID, duration = compileCode(seqName)
    except Exception as e:
        log(e)
        return

    variables = copy.deepcopy(MultiRun.currentlyRunningVariables) if MultiRun.currentlyRunningVariables is not None else copy.deepcopy(crate.variables)
    Playlist.sequenceCompiled(codeID, seqName, variables)

    if duration > 60 * 10:
        if not Design.confirmationDialog(
            "WARNING",
            f"sequence duration is {timedelta(seconds=duration)} long, are you sure you want to run?",
        ):
            return None

    try:
        generatedCodeFolderPath = crate.FileManager.cratePath + "generatedCode/" + datetime.now().strftime("%Y-%m-%d") + "/" + datetime.now().strftime("%H") + "/"
        if not os.path.exists(generatedCodeFolderPath):
            os.makedirs(generatedCodeFolderPath)
        codeFilePath = generatedCodeFolderPath + f"{codeID}.py"
        while os.path.exists(codeFilePath):
            codeID = codeID + 1
            codeFilePath = generatedCodeFolderPath + f"{codeID}.py"

        file = open(codeFilePath, "w")
        file.write(compiledCode)
        file.close()

        if settings.data["artiqMasterInWsl"]:
            # translating windows path to wsl path
            artiq_master_to_code_path = "/mnt/" + codeFilePath[0].lower() + codeFilePath[2:]
        else:
            artiq_master_to_code_path = codeFilePath
    except Exception as e:
        log("Error when compiling sequence: ")
        log(e)
        return
    try:
        expid = {
            "class_name": util.textToIdentifier(seqName),
            "file": artiq_master_to_code_path,
            "arguments": {"codeID": codeID},
            "log_level": 30,
            "repo_rev": "N/A",
            "duration": duration,
        }
        target = "master_schedule" if int(crate.Config.get("artiqVersion")) <= 7 else "schedule"
        scheduler = rpc.Client("127.0.0.1", crate.Config.get("port-control"), target)
        scheduler.submit(pipeline_name="main", expid=expid, priority=0, due_date=None, flush=False)
        scheduler.close_rpc()
    except ConnectionRefusedError as e:
        log(e)
    log(f"Sequence {seqName} submitted")


def stopRun():
    target = "master_schedule" if int(crate.Config.get("artiqVersion")) <= 7 else "schedule"
    try:
        scheduler = rpc.Client("127.0.0.1", crate.Config.get("port-control"), target)
        status = scheduler.get_status()
        for key in status.keys():
            scheduler.delete(key)
        scheduler.close_rpc()
    except ConnectionRefusedError as e:
        log(e)


def getDurationValue(seqName, seqStack=None):
    if seqStack is None:
        seqStack = []
    if seqName in seqStack:
        return float("inf")
    if seqName is not None and seqName != "" and seqName in crate.sequences:
        seqStack.append(seqName)
        value = 0
        for segName, segData in crate.sequences[seqName]["segments"].items():
            if segData["enabled"]:
                if segData["type"] == "portstate":
                    value += getSegmentDurationValue(segData)
                elif segData["type"] == "subsequence":
                    value += getSubsequenceDurationValue(segData, copy.deepcopy(seqStack))
        return value
    return None


def getSegmentDurationValue(segment):
    return Input.getValueFromState(segment["duration"], reader=float, replacer=Variables.replacer)


def getSubsequenceRepeatsValue(segment):
    return Input.getValueFromState(segment["repeats"], reader=int, replacer=Variables.replacer)


def getSubsequenceDurationValue(segment, seqStack=None):
    if seqStack is None:
        seqStack = []
    duration = getDurationValue(segment["subsequence"], seqStack)
    return duration * getSubsequenceRepeatsValue(segment)


def compileSequence(seqName, timeRunner, seqStack=None):
    if seqStack is None:
        seqStack = [seqName]
    else:
        if seqName in seqStack:
            return None
        seqStack.append(seqName)
    compiledSeq = []
    for segName, segData in crate.sequences[seqName]["segments"].items():
        if segData["enabled"]:
            if segData["type"] == "portstate":
                compiledSeg = compilePortStateSegment(seqName, segName, segData, timeRunner)
            elif segData["type"] == "subsequence":
                compiledSeg = compileSubsequenceSegment(segData, timeRunner, copy.deepcopy(seqStack))
            elif segData["type"] == "triggerwait":
                compiledSeg = compileTriggerWaitSegment(segData, timeRunner)
            if compiledSeg is None:
                return None
            for seg in compiledSeg:
                compiledSeq.append(seg)
    return compiledSeq


def compilePortStateSegment(seqName, segName, segData, timeRunner):
    durationValue = getSegmentDurationValue(segData)
    return [
        {
            "time": timeRunner.run(durationValue),
            "duration": durationValue,
            "single_duration": durationValue,
            "ports": compilePortStateDict(seqName, segName, segData["ports"]),
            "rpcs": compileRpcDict(seqName, segName, segData["rpcs"]),
        }
    ]


def compileSubsequenceSegment(segment, timeRunner, seqStack):
    duration = getDurationValue(segment["subsequence"])
    assert duration is not None, "Subsequence duration returned None"
    assert duration != float("inf"), f'Subsequence "{segment["subsequence"]}" contains itself'
    repeats = getSubsequenceRepeatsValue(segment)
    assert repeats is not None, "Subsequence repeats returned None"
    time = timeRunner.time
    timeRunner.run(duration * repeats)
    return [
        {
            "name": segment["subsequence"],
            "time": time,
            "single_duration": duration,
            "duration": duration * repeats,
            "repeats": repeats,
            "subsequence": compileSequence(segment["subsequence"], TimeRunner(), seqStack),
        }
    ]


def compileTriggerWaitSegment(segment, timeRunner):
    durationValue = getSegmentDurationValue(segment)
    return [
        {
            "time": timeRunner.run(durationValue),
            "duration": durationValue,
            "single_duration": durationValue,
            "input_ttl": crate.labsetup[segment["input_ttl"]]["device"],
        }
    ]


def compilePortStateDict(seqName, segName, portStateDict):
    COMPILE_FUNCTIONS = {
        "artiq.coredevice.ttl": compileTTL,
        "artiq.coredevice.zotino": compileDAC,
        "artiq.coredevice.fastino": compileDAC,
        "custom.CurrentDriver": compileDAC,
        "artiq.coredevice.sampler": compileSampler,
        "artiq.coredevice.ad9910": compileUrukul,
        "artiq.coredevice.adf5356": compileMirny,
    }
    compiledDict = {}
    for portName, portState in portStateDict.items():
        compiledDict[portName] = COMPILE_FUNCTIONS[crate.labsetup[portName]["module"]](portName, portState)
    return compiledDict


def compileTTL(portName, portState):
    return {
        "state": portState["state"] ^ crate.LabSetup.get(portName, "inverted"),
    }


def compileDAC(portName, portState):
    calibration_enabled = crate.labsetup[portName]["calibration_enabled"]
    calibration_unit_text = crate.labsetup[portName]["calibration_unit_text"]
    calibReader = None
    if calibration_enabled:
        calib_to_unit_factor = crate.labsetup[portName]["calibration_to_unit"]["factor"]
        if crate.labsetup[portName]["calibration_mode"] == "Formula":
            formula = crate.labsetup[portName]["calibration_formula"]

            def calibReader(text):
                return calib_to_unit_factor * eval(Formula.translateFormulaToNumpy(formula), {"x": float(text)})

        elif crate.labsetup[portName]["calibration_mode"] == "Dataset":
            calibReader = Dataset.getInterpolationReader(crate.labsetup[portName]["calibration_dataset"], calib_to_unit_factor)

    voltage_calibration_unit_selected = portState["voltage"]["unit"]["text"] == calibration_unit_text
    if voltage_calibration_unit_selected and not calibration_enabled:
        raise Exception("Calibration disabled but calibration unit still selected")
    compiledPortState = {}
    compiledPortState["voltage"] = Input.getValueFromState(
        portState["voltage"],
        reader=calibReader if voltage_calibration_unit_selected else float,
        replacer=Variables.replacer,
    )
    assert compiledPortState["voltage"] is not None, "Failed to get voltage"
    if portState["sweep_enable"]:
        sweep_voltage_calibration_unit_selected = portState["sweep_voltage"]["unit"]["text"] == calibration_unit_text
        if sweep_voltage_calibration_unit_selected and not calibration_enabled:
            raise Exception("Calibration disabled but calibration unit still selected")
        compiledPortState["sweep_voltage"] = Input.getValueFromState(
            portState["sweep_voltage"],
            reader=calibReader if sweep_voltage_calibration_unit_selected else float,
            replacer=Variables.replacer,
        )
        assert compiledPortState["sweep_voltage"] is not None, "Failed to get sweep voltage"
    compiledPortState["formula_text"] = "x"
    if portState["formula_enable"]:
        compiledPortState["formula_text"] = Input.getValueFromState(portState["formula_text"], reader=str, replacer=Variables.replacer)
        assert compiledPortState["formula_text"] is not None, "Failed to get formula text"
    return compiledPortState


def compileSampler(portName, portState):
    return {
        "freq": Input.getValueFromState(portState["freq"], reader=float, replacer=Variables.replacer),
    }


def compileUrukul(portName, portState):
    compiledPortState = {}
    compiledPortState["switch"] = portState["switch"] if portState["switch_enable"] else None
    compiledPortState["attenuation"] = Input.getValueFromState(portState["attenuation"], reader=float, replacer=Variables.replacer) if portState["attenuation_enable"] else None
    compiledPortState["mode"] = "normal"
    if portState["mode_enable"]:
        compiledPortState["amp"] = Input.getValueFromState(portState["amp"], reader=float, replacer=Variables.replacer)
        compiledPortState["freq"] = Input.getValueFromState(portState["freq"], reader=float, replacer=Variables.replacer)
        compiledPortState["phase"] = Input.getValueFromState(portState["phase"], reader=float, replacer=Variables.replacer)
        if portState["mode"] == "Sweep frequency":
            compiledPortState["mode"] = "sweep_freq"
            compiledPortState["sweep_freq"] = Input.getValueFromState(portState["sweep_freq"], reader=float, replacer=Variables.replacer)
            compiledPortState["sweep_duration"] = Input.getValueFromState(portState["sweep_duration"], reader=float, replacer=Variables.replacer) if portState["sweep_duration_enable"] else None
        if portState["mode"] == "Sweep amplitude":
            compiledPortState["mode"] = "sweep_amp"
            compiledPortState["sweep_amp"] = Input.getValueFromState(portState["sweep_amp"], reader=float, replacer=Variables.replacer)
            compiledPortState["sweep_duration"] = Input.getValueFromState(portState["sweep_duration"], reader=float, replacer=Variables.replacer) if portState["sweep_duration_enable"] else None 

        if portState["mode"] == "Write RAM Profile":
            compiledPortState["mode"] = "ram_write"
            compiledPortState["ram_profile"] = portState["ram_profile"]
            compiledPortState["ram_start"] = portState["ram_start"]
            compiledPortState["ram_end"] = portState["ram_end"]
            compiledPortState["ram_step_size"] = portState["ram_step_size"]
            compiledPortState["ram_phase_formula"] = Formula.translateFormulaToNumpy(Variables.replacer(portState["ram_phase_formula"]))
            compiledPortState["ram_amplitude_formula"] = Formula.translateFormulaToNumpy(Variables.replacer(portState["ram_amplitude_formula"]))
            compiledPortState["ram_frequency_formula"] = Formula.translateFormulaToNumpy(Variables.replacer(portState["ram_frequency_formula"]))
            compiledPortState["ram_destination"] = portState["ram_destination"]
            compiledPortState["ram_mode"] = portState["ram_mode"]
        if portState["mode"] == "Execute RAM Profile":
            compiledPortState["mode"] = "ram_execute"
            compiledPortState["ram_profile"] = portState["ram_profile"]
    return compiledPortState


def compileMirny(portName, portState):
    compiledPortState = {}
    compiledPortState["freq"] = Input.getValueFromState(portState["freq"], reader=float, replacer=Variables.replacer) if portState["freq_enable"] else None
    compiledPortState["attenuation"] = Input.getValueFromState(portState["attenuation"], reader=float, replacer=Variables.replacer) if portState["attenuation_enable"] else None
    compiledPortState["switch"] = portState["switch"] if portState["switch_enable"] else None
    compiledPortState["skipInit"] = portState["skipInit"] if "skipInit" in portState else False
    compiledPortState["useAlmazny"] = portState["useAlmazny"] if "useAlmazny" in portState else False
    return compiledPortState


def compileRpcDict(seqName, segName, rpcDict):
    compiledRpcDict = {}
    for rpcName, rpcData in rpcDict.items():
        args = []
        argData = crate.Sequences.getRPCValue(seqName, segName, rpcName, "args")
        kargData = crate.Sequences.getRPCValue(seqName, segName, rpcName, "kargs")
        for arg in argData.split(" "):
            if arg == "":
                continue
            arg = Input.getValueFromState(arg, reader=RPC.argReader, replacer=Variables.replacer)
            try:
                args.append(int(arg))
            except Exception:
                try:
                    args.append(float(arg))
                except Exception:
                    args.append(arg)
        kargs = {}
        for k, v in kargData.items():
            kargs[k] = Variables.replacer(v)
        compiledRpcDict[rpcName] = {"args": args, "kargs": kargs}
    return compiledRpcDict
