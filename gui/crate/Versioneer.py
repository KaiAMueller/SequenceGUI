import os

import gui.crate as crate
import gui.util as util
import gui.widgets.Design as Design

# units are also dict now storing factor as well (e.g. "unit": "MHz" -> "unit": {"text": "MHz", "factor": 1e6})
DEFAULT_UNIT_FACTORS = {
    "Hz": 1,
    "kHz": 1e3,
    "MHz": 1e6,
    "GHz": 1e9,
    "ns": 1e-9,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1,
    "dB": 1,
    "V": 1,
    "mV": 1e-3,
}


def updateUnit(unit):
    if type(unit) is dict:
        return unit
    if unit in DEFAULT_UNIT_FACTORS:
        factor = DEFAULT_UNIT_FACTORS[unit]
    else:
        factor = 1
    return {"text": unit, "factor": factor}


def updateThisDictUnits(d):
    for valueName, valueData in d.items():
        if type(valueData) is dict and "unit" in valueData and "text" in valueData and type(valueData["unit"]) is str:
            valueData["unit"] = updateUnit(valueData["unit"])


def updateTo_0_3():
    # converting sequences segments from list to dict
    for seqName, seqData in crate.sequences.items():
        if "segments" in seqData and type(seqData["segments"]) is list:
            segments = {}
            for i in range(len(seqData["segments"])):
                segments[str(i)] = seqData["segments"][i]
            seqData["segments"] = segments

    # rename sequences, only allow letters, numbers and underscores
    for seqName in list(crate.sequences.keys()):
        if not seqName.isidentifier():
            newName = util.textToIdentifier(seqName)
            while newName in crate.sequences:
                newName += "_"
            crate.sequences[newName] = crate.sequences.pop(seqName)
            # renaming subsequence appearances
            for seqData in crate.sequences.values():
                if seqData["isDir"]:
                    continue
                for segData in seqData["segments"].values():
                    if segData["type"] == "subsequence" and segData["subsequence"] == seqName:
                        segData["subsequence"] = newName

    # rename ports, only allow letters, numbers and underscores
    for portName in list(crate.labsetup.keys()):
        if not portName.isidentifier():
            newName = util.textToIdentifier(portName)
            while newName in crate.labsetup:
                newName += "_"
            crate.labsetup[newName] = crate.labsetup.pop(portName)
            # renaming sequence appearances
            for seqData in crate.sequences.values():
                if seqData["isDir"]:
                    continue
                for segData in seqData["segments"].values():
                    if segData["type"] == "portstate" and portName in segData["ports"]:
                        segData["ports"][newName] = segData["ports"].pop(portName)

    # remove name key from sequences
    for seqName, seqData in crate.sequences.items():
        if "name" in seqData:
            seqData.pop("name")

    for portName, portData in crate.labsetup.items():
        # update attenuation values from float to dict
        if "timeshift" in portData:
            portData.pop("timeshift")
        if "timeshift_val" in portData:
            portData.pop("timeshift_val")
        if portData["module"] in [
            "artiq.coredevice.adf5356",
            "artiq.coredevice.ad9910",
        ]:
            if "attenuation" in portData and type(portData["attenuation"]) is float:
                portData["attenuation"] = {
                    "text": str(portData["attenuation"]),
                    "unit": {"text": "dB", "factor": 1},
                }
        elif portData["module"] in [
            "artiq.coredevice.zotino",
            "artiq.coredevice.fastino",
        ]:
            if "channel" in portData and type(portData["channel"]) is int:
                portData["channel"] = str(portData["channel"])
            if "calibration" in portData:
                portData.pop("calibration")

    # adding rpcs to segments
    for seqName, seqData in crate.sequences.items():
        for segName, segData in seqData["segments"].items():
            if segData["type"] == "portstate" and "rpcs" not in segData:
                segData["rpcs"] = {}

    # subsequence repeats from dict to str
    for seqName, seqData in crate.sequences.items():
        for segName, segData in seqData["segments"].items():
            if segData["type"] == "subsequence" and "repeats" in segData and type(segData["repeats"]) is dict:
                segData["repeats"] = segData["repeats"]["text"]

    # adding appearances to sequences
    for seqName, seqData in crate.sequences.items():
        seqData["appearances"] = {}
    for seqName, seqData in crate.sequences.items():
        for segName, segData in seqData["segments"].items():
            if segData["type"] == "subsequence":
                if seqName not in crate.sequences[segData["subsequence"]]["appearances"]:
                    crate.sequences[segData["subsequence"]]["appearances"][seqName] = [segName]
                else:
                    crate.sequences[segData["subsequence"]]["appearances"][seqName].append(segName)

    for seqName, seqData in crate.sequences.items():
        for segName, segData in seqData["segments"].items():
            if "ports" in segData:
                for portName, portData in segData["ports"].items():
                    module = crate.labsetup[portName]["module"]
                    # renaming dac state to voltage
                    if module in [
                        "artiq.coredevice.zotino",
                        "artiq.coredevice.fastino",
                    ]:
                        if "state" in portData:
                            portData["voltage"] = portData.pop("state")
                        if "sweep" in portData:
                            portData["sweep_voltage"] = portData.pop("sweep")
                    # renaming dds stuff
                    if module in [
                        "artiq.coredevice.ad9910",
                        "artiq.coredevice.adf5356",
                    ]:
                        if "freq_val" in portData:
                            portData["freq"] = {
                                "text": str(portData.pop("freq_val") / 1e6),
                                "unit": {"text": "MHz", "factor": 1e6},
                            }
                        if "stopfreq_val" in portData:
                            portData["sweep_freq"] = {
                                "text": str(portData.pop("stopfreq_val") / 1e6),
                                "unit": {"text": "MHz", "factor": 1e6},
                            }
                        if "enable" in portData:
                            portData["switch"] = portData.pop("enable")
                            portData["switch_enable"] = True
                        if "ram_mod_freq" in portData and type(portData["ram_mod_freq"]) is str:
                            unitStr = portData.pop("ram_mod_freq_unit") if "ram_mod_freq_unit" in portData else "MHz"
                            portData["ram_mod_freq"] = {
                                "text": str(portData["ram_mod_freq"]),
                                "unit": updateUnit(unitStr),
                            }
                    # cleaning up ttl
                    if module in ["artiq.coredevice.ttl"]:
                        if "state" in portData and type(portData["state"]) is str:
                            portData["state"] = portData["state"] == "on"
                    if module in ["artiq.coredevice.sampler"]:
                        if "freq_val" in portData:
                            portData["freq"] = {
                                "text": str(portData.pop("freq_val")),
                                "unit": {"text": "Hz", "factor": 1},
                            }

                    # cleanup remaining stuff
                    for valueName in list(portData.keys()):
                        if valueName not in crate.Sequences.DEFAULT_PORTSTATE_VALUES[module]:
                            portData.pop(valueName)

    for seqName, seqData in crate.sequences.items():
        for segName, segData in seqData["segments"].items():
            updateThisDictUnits(segData)  # updating segments
            if "ports" in segData:
                for portName, portData in segData["ports"].items():
                    updateThisDictUnits(portData)  # updating ports
    for portName, portData in crate.labsetup.items():
        updateThisDictUnits(portData)  # updating labsetup
        if "calibration_unit" in portData:
            portData["calibration_unit_text"] = portData.pop("calibration_unit")
        if "calibration_to_unit" in portData:
            portData["calibration_to_unit"] = updateUnit(portData["calibration_to_unit"])

        # cleanup remaining stuff
        for valueName in list(portData.keys()):
            if valueName not in crate.LabSetup.DEFAULT_VALUES[portData["module"]] and valueName not in ["module", "device"]:
                portData.pop(valueName)

    # add dimensions to multiruns
    for multirunName, multirunData in crate.multiruns.items():
        if "dimensions" not in multirunData:
            multirunData["dimensions"] = {}
        if "variables" in multirunData:
            dimension = 0
            for varName, varData in multirunData["variables"].items():
                multirunData["dimensions"]["dim" + str(dimension)] = {
                    "steps": varData.pop("steps"),
                    "variables": {varName: varData},
                }
                dimension += 1
            multirunData.pop("variables")
    return "0.3"


def updateTo_0_4():
    # moving rpc scripts to their own files in script folder
    for rpcName, rpcData in crate.rpcs.items():
        if "script" in rpcData:
            script = rpcData["script"]
            if "file" not in rpcData:
                rpcData["file"] = rpcName + ".py"
            path = crate.FileManager.getScriptsPath() + rpcData["file"]
            if not os.path.isfile(path):
                file = open(path, "w")
                file.write(script)
                file.close()
            rpcData.pop("script")

    # renaming multirun mode from linear scan to scan
    for multirunData in crate.multiruns.values():
        if multirunData["mode"] == "linear scan":
            multirunData["mode"] = "scan"
    return "0.4"


def updateTo_0_4_1():
    # adding isDir key to all sequences, variables, mutliruns, rpcs and labsetup dicts
    for data in [
        crate.sequences,
        crate.variables,
        crate.multiruns,
        crate.rpcs,
        crate.labsetup,
    ]:
        for key in data:
            if "isDir" not in data[key]:
                data[key]["isDir"] = False
    return "0.4.1"


def updateTo_0_4_2():
    # check if mirny has almazny
    for portData in crate.labsetup.values():
        if "module" in portData and portData["module"] == "artiq.coredevice.adf5356":
            portData["hasAlmazny"] = False
            for device in crate.device_db:
                if "class" in crate.device_db[device] and crate.device_db[device]["class"] == "Almazny":
                    if crate.device_db[device]["arguments"]["host_mirny"] == crate.device_db[portData["device"]]["arguments"]["cpld_device"]:
                        portData["hasAlmazny"] = True
                        break
    return "0.4.2"


def updateTo_0_5():
    # rename freq_enable to mode_enable
    for seqData in crate.sequences.values():
        for segData in seqData["segments"].values():
            if "ports" in segData:
                for portName, portData in segData["ports"].items():
                    if crate.labsetup[portName]["module"] == "artiq.coredevice.ad9910":
                        if "freq_enable" in portData:
                            portData["mode_enable"] = portData.pop("freq_enable")
    return "0.5"


VERSION = "0.5"
UPDATE_FUNCTIONS = {
    "default": updateTo_0_3,
    "0.3": updateTo_0_4,
    "0.4": updateTo_0_4_1,
    "0.4.1": updateTo_0_4_2,
    "0.4.2": updateTo_0_5,
}


def checkUpdate():
    # updateTo_0_3()
    # if no version is defined its before 0.3 because thats when versioning was introduced
    if "version" not in crate.config:
        crate.config["version"] = "0.2"

    if crate.config["version"] != VERSION:
        Design.infoDialog(
            "Update",
            f"Crate Version {crate.config['version']} detected. Updating all project data to {VERSION}.",
        )
        if crate.config["version"] not in UPDATE_FUNCTIONS:
            crate.config["version"] = "default"

        # run through all version udpate functions until the current version is reached
        while crate.config["version"] in UPDATE_FUNCTIONS and crate.config["version"] != VERSION:
            crate.config["version"] = UPDATE_FUNCTIONS[crate.config["version"]]()
