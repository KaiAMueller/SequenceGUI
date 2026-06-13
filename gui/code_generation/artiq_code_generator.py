import json

import gui.code_generation.event_builder as event_builder
import gui.crate as crate
import gui.crate.FileManager
import gui.settings as settings
import gui.util as util
import gui.widgets.RPC

externalInitGenerators = []
externalPrepareGenerators = []
externalImportGenerators = []
externalFunctionGenerators = []
externalAnalyzeGenerators = []
externalFunctionGenerators = []
externalBuildGenerators = []


def generateImportCodeTokens(events):
    imports = []

    # collect all unique imports
    for currentEvents in events:
        if "repeats" in currentEvents:
            newImports = generateImportCodeTokens(currentEvents["events"])
            for code in newImports:
                if code not in imports:
                    imports.append(code)
        else:
            for event in currentEvents["events"]:
                code = event.generateImportCode()
                if code is None:
                    continue
                if code not in imports:
                    imports.append(code)

    for externalGenerator in externalImportGenerators:
        externalImports = externalGenerator()
        for externalImport in externalImports:
            if externalImport not in imports:
                imports.append(externalImport)
    return imports


def generateImportCode(events):
    return "\n".join(generateImportCodeTokens(events))


def generateBuildCode(devices):
    numberValuePara = "ndecimals" if int(crate.Config.get("artiqVersion")) <= 7 else "precision"
    buildCode = f"""
        self.setattr_argument("codeID", NumberValue(type="int", {numberValuePara}=0, scale=1, step=1))"""

    # insert used device names into code template
    for device in devices:
        buildCode += f"""
        self.setattr_device("{device.name}")"""

    for externalGenerator in externalBuildGenerators:
        externalBuild = externalGenerator()
        buildCode += externalBuild

    for device in devices:
        code = device.generateBuildCode()
        if code is not None:
            buildCode += code

    return buildCode


def generatePrepareCode(events, name="", jsonString="", firstTime=True):
    prepareCode = ""
    if firstTime:
        prepareCode += f"""self.set_dataset("sequenceJson", '{jsonString}')"""

    # set time stamp indices
    indexCounter = 0
    for currentEvents in events:
        if "repeats" in currentEvents:
            for event in currentEvents["events"]:
                if type(event) is dict:
                    event["timeIndex"] = indexCounter
                else:
                    event.timeIndex = indexCounter
            if not settings.getRelativeTimestampsEnabled():
                prepareCode += f"""
        self.duration_{currentEvents["name"]} = self.core.seconds_to_mu({currentEvents["single_duration"]})
        self.timestamp_{name}{indexCounter} = self.core.seconds_to_mu({currentEvents["time"]})"""
            prepareCode += generatePrepareCode(currentEvents["events"], currentEvents["name"], firstTime=False)
            currentEvents["timeIndex"] = indexCounter
            indexCounter += 1
        else:
            for event in currentEvents["events"]:
                if type(event) is dict:
                    event["timeIndex"] = indexCounter
                else:
                    event.timeIndex = indexCounter
            if settings.getRelativeTimestampsEnabled():
                timeCursorShift = sum([event.getTimeCursorShift() for event in currentEvents["events"]])
                delay = currentEvents["duration"] - timeCursorShift
                assert delay >= 0, f"Delay is negative for event {currentEvents['name']}"
                prepareCode += f"""
        self.delay_{name}{indexCounter} = self.core.seconds_to_mu({delay})"""
            else:
                prepareCode += f"""
        self.timestamp_{name}{indexCounter} = self.core.seconds_to_mu({currentEvents["time"]})"""
            currentEvents["timeIndex"] = indexCounter
            indexCounter += 1
            # get and append the prepare code of every event
            for event in currentEvents["events"]:
                code = event.generatePrepareCode()
                if code is not None:
                    prepareCode += code
    for externalGenerator in externalPrepareGenerators:
        externalPrepares = externalGenerator()
        for externalPrepare in externalPrepares:
            prepareCode += externalPrepare

    return prepareCode


def generateInitCode(devices):
    initCode = ""

    for externalGenerator in externalInitGenerators:
        externalInits = externalGenerator()
        for externalInits in externalInits:
            initCode += externalInits

    # sort by priority so that nothing goes before the core initialization
    devices.sort(key=lambda x: -x.priority)

    # get and append the init code of every device
    for device in devices:
        code = device.generateInitCode()
        if code is not None:
            initCode += code

    if initCode == "":
        initCode = """
        pass"""

    return initCode


def generateRunCode(events, name="", forLoopIndex=0, start_time_variable="start_mu"):
    runCode = ""

    # loop over timesteps
    for currentEvents in events:
        if "repeats" in currentEvents:
            time_add = f"""i{forLoopIndex} * self.duration_{currentEvents["name"]}"""
            repeatedRunCode = generateRunCode(
                currentEvents["events"],
                currentEvents["name"],
                forLoopIndex + 1,
                f"""{start_time_variable} + self.timestamp_{name}{currentEvents["timeIndex"]} + {time_add}""",
            ).replace("\n", "\n    ")
            if repeatedRunCode == "":
                continue
            runCode += f"""
        for i{forLoopIndex} in range({currentEvents["repeats"]}):"""
            runCode += repeatedRunCode
        else:
            if not settings.getRelativeTimestampsEnabled():
                runCode += f"""
        at_mu({start_time_variable} + self.timestamp_{name}{currentEvents["timeIndex"]})"""
            currentEvents["events"].sort(key=lambda x: -x.priority)
            for event in currentEvents["events"]:
                code = event.generateRunCode()
                if code is not None:
                    runCode += code
            if settings.getRelativeTimestampsEnabled():
                runCode += f"""
        delay_mu(self.delay_{name}{currentEvents["timeIndex"]})"""

    return runCode


def generateAnalyzeCode(events):
    analyzeCode = ""

    # get and append the analyze code of every event
    for currentEvents in events:
        if "repeats" in currentEvents:
            analyzeCode += generateAnalyzeCode(currentEvents["events"])
        else:
            for event in currentEvents["events"]:
                code = event.generateAnalyzeCode()
                if code is not None:
                    analyzeCode += code

    if analyzeCode == "":
        analyzeCode = """
        pass"""

    for externalGenerator in externalAnalyzeGenerators:
        externalAnalyses = externalGenerator()
        for externalAnalyse in externalAnalyses:
            analyzeCode += externalAnalyse
    return analyzeCode


def generateFunctionCode(devices):
    functions = []
    for device in devices:
        for function in device.functions:
            if function not in functions:
                functions.append(function)

    for externalGenerator in externalFunctionGenerators:
        externalFunctions = externalGenerator()
        for externalFunction in externalFunctions:
            if externalFunction not in functions:
                functions.append(externalFunction)
    return "\n".join(functions)


def generateCode(seqName, sequenceJson, codeID):
    jsonString = json.dumps(sequenceJson)

    event_builder.preProccess(sequenceJson)
    devices, events = event_builder.generateDevicesAndEvents(sequenceJson)

    importCode = generateImportCode(events)
    buildCode = generateBuildCode(devices)
    prepareCode = generatePrepareCode(events, name="", jsonString=jsonString)
    initCode = generateInitCode(devices)
    runCode = generateRunCode(events)
    analyzeCode = generateAnalyzeCode(events)
    functionCode = generateFunctionCode(devices)
    className = util.textToIdentifier(seqName)

    return f"""
from artiq.experiment import *
from artiq.coredevice.ad9910 import (PHASE_MODE_TRACKING, PHASE_MODE_ABSOLUTE, RAM_DEST_ASF, RAM_DEST_POW, RAM_DEST_FTW, RAM_DEST_POWASF, RAM_MODE_DIRECTSWITCH, RAM_MODE_RAMPUP, RAM_MODE_BIDIR_RAMP, RAM_MODE_CONT_RAMPUP, RAM_MODE_CONT_BIDIR_RAMP, _AD9910_REG_RAM)
from artiq.coredevice import urukul
from artiq.coredevice import spi2 as spi
import numpy as np
{importCode}

class {className}(EnvExperiment):

    def build(self):{buildCode}

{functionCode}

    def prepare(self):
        if self.codeID != {codeID}:
            raise AssertionError("Sequence Control tried to execute the wrong generated code. Maybe wrong artiq_master running? I am {codeID}, but got " + str(self.codeID))
        {prepareCode}        

    @kernel
    def init(self):{initCode}

    @kernel
    def run(self):
        self.core.break_realtime()
        self.init()
        delay(5*ms)
        self.core.break_realtime()
        self.{gui.widgets.RPC.device_name}.sequenceStarted(\"{codeID}\", \"{seqName}\")
        self.core.break_realtime()
        delay(5*ms)
        start_mu = now_mu()
        {runCode}
        delay(5*ms)
        self.core.wait_until_mu(now_mu())
        self.{gui.widgets.RPC.device_name}.sequenceFinished(\"{codeID}\", \"{seqName}\")

    def analyze(self):{analyzeCode}
    """
