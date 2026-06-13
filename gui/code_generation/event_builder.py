import gui.crate as crate
import gui.util as util
import gui.widgets.RPC

from .device.Core import CoreDevice
from .device.CurrentDriver import CurrentDriver
from .device.Fastino import Fastino
from .device.Mirny import Mirny, MirnyCPLD
from .device.RPC import RPC
from .device.Sampler import Sampler
from .device.TTL import TTL
from .device.Urukul import Urukul, UrukulCPLD
from .device.Zotino import Zotino
from .event.CurrentDriver import CurrentDriverEvent
from .event.Fastino import FastinoEvent
from .event.Mirny import MirnyEvent
from .event.RPC import RPCEvent
from .event.Sampling import SampleEvent
from .event.TTL import TTLEvent, TTLTriggerEvent
from .event.Urukul import UrukulEvent, UrukulRamEvent, UrukulSweepEvent
from .event.Wait import WaitEvent
from .event.Zotino import ZotinoEvent


def preProccess(sequenceJson):
    iterateSequencePorts(sequenceJson, summarizeZotinoChannels)
    iterateSequencePorts(sequenceJson, summarizeFastinoChannels)


def iterateSequencePorts(sequenceJson, function):
    for segment in sequenceJson:
        if "subsequence" in segment:
            iterateSequencePorts(segment["subsequence"], function)
        else:
            function(segment)


def summarizeZotinoChannels(portStateDict):
    if "ports" not in portStateDict:
        return
    # preprocess zotino (make multiple events of same device on different channels at same time a single event)
    # dictionary spaghetti, dont get a headache
    zotinoDevices = {}  # remember used zotino devices for this time step
    for portName in portStateDict["ports"]:  # iterate all channels
        portState = portStateDict["ports"][portName]
        setup = crate.labsetup[portName]
        if setup["module"] == "artiq.coredevice.zotino":  # checks if its a zotino
            if setup["device"] in zotinoDevices:  # if this device already used in this timesteps (means its a different channel)
                zotinoDevices[setup["device"]]["channels"][setup["channel"]] = portState  # add to previous "main portState" event of same device
            else:
                portState["channels"] = {  # first event of this device at this time
                    setup["channel"]: portState,
                }
                zotinoDevices[setup["device"]] = portState  # add to used device dictionary and make this the "main portState" for this device


def summarizeFastinoChannels(portStateDict):
    if "ports" not in portStateDict:
        return
    # preprocess fastino (make multiple events of same device on different channels at same time a single event)
    # dictionary spaghetti, dont get a headache
    fastinoDevices = {}  # remember used zotino devices for this time step
    for portName in portStateDict["ports"]:  # iterate all channels
        portState = portStateDict["ports"][portName]
        setup = crate.labsetup[portName]
        if setup["module"] == "artiq.coredevice.fastino":  # checks if its a zotino
            if setup["device"] in fastinoDevices:  # if this device already used in this timesteps (means its a different channel)
                fastinoDevices[setup["device"]]["channels"][setup["channel"]] = portState  # add to previous "main portState" event of same device
            else:
                portState["channels"] = {  # first event of this device at this time
                    setup["channel"]: portState,
                }
                fastinoDevices[setup["device"]] = portState  # add to used device dictionary and make this the "main portState" for this device


def generateDevicesAndEvents(sequenceJson):
    usedZotinos = {}  # avoid duplicate zotinos
    usedFastinos = {}  # avoid duplicate zotinos
    usedSamplers = {}  # avoid duplicate zotinos
    urukulCplds = {}  # add urukul cpld device to urukul ad9910
    mirnyCplds = {}  # add mirny cpld device to mirny adf5356

    # create devices and their events
    devicesDict = {
        "core": CoreDevice(),
        gui.widgets.RPC.device_name: RPC(gui.widgets.RPC.device_name),
    }
    devices = []
    events = []

    iterateSequencePorts(
        sequenceJson,
        lambda portState: addDevice(
            portState,
            devicesDict,
            usedZotinos,
            urukulCplds,
            usedSamplers,
            mirnyCplds,
            usedFastinos,
        ),
    )
    generateEventsRecursive(sequenceJson, devicesDict, events)
    generateDeviceList(devicesDict, devices)
    lastEventEnd = 0
    for event in events:
        if event["time"] + event["duration"] > lastEventEnd:
            lastEventEnd = event["time"] + event["duration"]
    events.append(
        {
            "time": lastEventEnd,
            "duration": 0,
            "events": [WaitEvent(lastEventEnd, 0, devicesDict["core"])],
        }
    )

    return devices, events


def addDevice(
    portState,
    devicesDict,
    usedZotinos,
    urukulCplds,
    usedSamplers,
    mirnyCplds,
    usedFastinos,
):
    if "ports" not in portState:
        if "input_ttl" in portState:
            if portState["input_ttl"] not in devicesDict:
                devicesDict[portState["input_ttl"]] = TTL(portState["input_ttl"], mode="input")
        return
    for portName in portState["ports"]:
        if portName not in devicesDict:
            if crate.labsetup[portName]["module"] == "artiq.coredevice.ttl":
                device = TTL(crate.labsetup[portName]["device"])
            elif crate.labsetup[portName]["module"] == "artiq.coredevice.zotino":
                zotinoDeviceName = crate.labsetup[portName]["device"]
                if zotinoDeviceName in usedZotinos:
                    device = usedZotinos[zotinoDeviceName]
                else:
                    device = Zotino(zotinoDeviceName)
                    usedZotinos[zotinoDeviceName] = device
            elif crate.labsetup[portName]["module"] == "artiq.coredevice.fastino":
                fastinoDeviceName = crate.labsetup[portName]["device"]
                if fastinoDeviceName in usedFastinos:
                    device = usedFastinos[fastinoDeviceName]
                else:
                    device = Fastino(fastinoDeviceName)
                    usedFastinos[fastinoDeviceName] = device
            elif crate.labsetup[portName]["module"] == "artiq.coredevice.ad9910":
                deviceName = crate.labsetup[portName]["device"]
                cpldName = crate.device_db[deviceName]["arguments"]["cpld_device"]
                if cpldName not in urukulCplds:
                    urukulCplds[cpldName] = UrukulCPLD(cpldName)
                device = Urukul(deviceName, urukulCplds[cpldName])
            elif crate.labsetup[portName]["module"] == "artiq.coredevice.sampler":
                samplerDeviceName = crate.labsetup[portName]["device"]
                if samplerDeviceName in usedSamplers:
                    device = usedSamplers[samplerDeviceName]
                else:
                    device = Sampler(samplerDeviceName)
                    usedSamplers[samplerDeviceName] = device
            elif crate.labsetup[portName]["module"] == "artiq.coredevice.adf5356":
                deviceName = crate.labsetup[portName]["device"]
                cpldName = crate.device_db[deviceName]["arguments"]["cpld_device"]
                if cpldName not in mirnyCplds:
                    mirnyCplds[cpldName] = MirnyCPLD(cpldName)
                device = Mirny(deviceName, mirnyCplds[cpldName])
            elif crate.labsetup[portName]["module"] == "custom.CurrentDriver":
                device = CurrentDriver(crate.labsetup[portName]["device"])
            else:
                raise NotImplementedError(crate.labsetup[portName]["module"] + " device not implemented")
            devicesDict[portName] = device


def generateEventsRecursive(sequenceJson, devicesDict, events):
    for segment in sequenceJson:
        if "ports" in segment:
            generateAndAppendCurrentEvents(segment, devicesDict, events)
        elif "input_ttl" in segment:
            generateTriggerWaitEvent(segment, devicesDict, events)
        elif "subsequence" in segment:
            if segment["repeats"] > 0:
                subEvents = []
                generateEventsRecursive(segment["subsequence"], devicesDict, subEvents)
                events.append(
                    {
                        "time": segment["time"],
                        "duration": segment["duration"],
                        "single_duration": segment["single_duration"],
                        "repeats": segment["repeats"],
                        "name": util.textToIdentifier(segment["name"]),
                        "events": subEvents,
                    }
                )
        else:
            raise ("invalid sequenceJson")


def generateTriggerWaitEvent(segment, devicesDict, events):
    event = TTLTriggerEvent(
        time=segment["time"],
        duration=segment["duration"],
        device=devicesDict[segment["input_ttl"]],
    )
    events.append({"time": segment["time"], "duration": segment["duration"], "events": [event]})


def generateAndAppendCurrentEvents(segment, devicesDict, events):
    currentEvents = []
    for rpcName, rpcData in segment["rpcs"].items():
        event = RPCEvent(
            time=segment["time"],
            duration=segment["duration"],
            device=devicesDict[gui.widgets.RPC.device_name],
            name=rpcName,
            args=rpcData["args"],
            kargs=rpcData["kargs"],
        )
        currentEvents.append(event)
    for portName, portState in segment["ports"].items():
        event = None
        device = devicesDict[portName]
        if crate.labsetup[portName]["module"] == "artiq.coredevice.ttl":
            event = TTLEvent(
                time=segment["time"],
                duration=segment["duration"],
                device=device,
                state=portState["state"],
            )
        elif crate.labsetup[portName]["module"] == "artiq.coredevice.zotino":
            if "channels" in portState:  # if its not included, its included in another event of same device (see preprocess above)
                event = ZotinoEvent(
                    time=segment["time"],
                    duration=segment["duration"],
                    device=device,
                    channels=portState["channels"],
                )
        elif crate.labsetup[portName]["module"] == "artiq.coredevice.fastino":
            if "channels" in portState:  # if its not included, its included in another event of same device (see preprocess above)
                event = FastinoEvent(
                    time=segment["time"],
                    duration=segment["duration"],
                    device=device,
                    channels=portState["channels"],
                )
        elif crate.labsetup[portName]["module"] == "artiq.coredevice.sampler":
            event = SampleEvent(
                time=segment["time"],
                duration=segment["duration"],
                device=device,
                sampleRate=portState["freq"],
            )
        elif crate.labsetup[portName]["module"] == "artiq.coredevice.ad9910":
            if portState["mode"] in ["ram_write", "ram_execute"]:
                event = UrukulRamEvent(
                    time=segment["time"],
                    duration=segment["duration"],
                    device=device,
                    switch=portState["switch"] if "switch" in portState else None,
                    freq=portState["freq"] if "freq" in portState else None,
                    amp=portState["amp"] if "amp" in portState else None,
                    phase=portState["phase"] if "phase" in portState else None,
                    attenuation=(portState["attenuation"] if "attenuation" in portState else None),
                    only_execute=(portState["mode"] == "ram_execute"),
                    ram_amplitude_formula=(portState["ram_amplitude_formula"] if "ram_amplitude_formula" in portState else None),
                    ram_phase_formula=(portState["ram_phase_formula"] if "ram_phase_formula" in portState else None),
                    ram_frequency_formula=(portState["ram_frequency_formula"] if "ram_frequency_formula" in portState else None),
                    ram_profile=(portState["ram_profile"] if "ram_profile" in portState else None),
                    ram_start=(portState["ram_start"] if "ram_start" in portState else None),
                    ram_end=(portState["ram_end"] if "ram_end" in portState else None),
                    ram_step_size=(portState["ram_step_size"] if "ram_step_size" in portState else None),
                    ram_destination=(portState["ram_destination"] if "ram_destination" in portState else None),
                    ram_mode=(portState["ram_mode"] if "ram_mode" in portState else None),
                )
            elif portState["mode"] == "sweep_freq":
                event = UrukulSweepEvent(
                    time=segment["time"],
                    duration=segment["duration"],
                    device=device,
                    switch=portState["switch"] if "switch" in portState else None,
                    freq=portState["freq"] if "freq" in portState else None,
                    amp=portState["amp"] if "amp" in portState else None,
                    attenuation=(portState["attenuation"] if "attenuation" in portState else None),
                    sweep_freq=portState["sweep_freq"],
                    sweep_duration=portState["sweep_duration"],
                )
            elif portState["mode"] == "sweep_amp":
                event = UrukulSweepEvent(
                    time=segment["time"],
                    duration=segment["duration"],
                    device=device,
                    switch=portState["switch"] if "switch" in portState else None,
                    freq=portState["freq"] if "freq" in portState else None,
                    amp=portState["amp"] if "amp" in portState else None,
                    attenuation=(portState["attenuation"] if "attenuation" in portState else None),
                    sweep_amp=portState["sweep_amp"],
                    sweep_duration=portState["sweep_duration"],
                )
            else:
                event = UrukulEvent(
                    time=segment["time"],
                    duration=segment["duration"],
                    device=device,
                    switch=portState["switch"] if "switch" in portState else None,
                    amp=portState["amp"] if "amp" in portState else None,
                    freq=portState["freq"] if "freq" in portState else None,
                    phase=portState["phase"] if "phase" in portState else None,
                    attenuation=(portState["attenuation"] if "attenuation" in portState else None),
                )
        elif crate.labsetup[portName]["module"] == "artiq.coredevice.adf5356":
            almaznyDeviceName = None
            if portState["useAlmazny"]:
                for d in crate.device_db:
                    if "class" in crate.device_db[d] and crate.device_db[d]["class"] == "Almazny":
                        if crate.device_db[d]["arguments"]["host_mirny"] == device.cpld.name:
                            almaznyDeviceName = d
                            break
                assert almaznyDeviceName is not None, "No almazny device found for mirny device " + device.name
            event = MirnyEvent(
                time=segment["time"],
                duration=segment["duration"],
                device=device,
                switch=portState["switch"],
                freq=portState["freq"],
                attenuation=portState["attenuation"],
                skipInit=portState["skipInit"],
                useAlmazny=portState["useAlmazny"],
                almaznyDeviceName=almaznyDeviceName,
            )
        elif crate.labsetup[portName]["module"] == "custom.CurrentDriver":
            event = CurrentDriverEvent(
                time=segment["time"],
                duration=segment["duration"],
                device=device,
                voltage=portState["voltage"],
                sweep_voltage=(portState["sweep_voltage"] if "sweep_voltage" in portState else None),
                formula_text=(portState["formula_text"] if "formula_text" in portState else None),
            )
        else:
            raise NotImplementedError(crate.labsetup[portName]["module"] + " not implemented")
        if event is not None:
            currentEvents.append(event)
    events.append(
        {
            "time": segment["time"],
            "duration": segment["duration"],
            "events": currentEvents,
        }
    )


def generateDeviceList(devicesDict, devices):
    for deviceName in devicesDict:
        device = devicesDict[deviceName]
        if device not in devices and (len(device.events) > 0 or device.important):  # avoid double devices and only include if device has events
            devices.append(device)
            for relatedDevice in device.relatedDevices:
                if relatedDevice not in devices:
                    devices.append(relatedDevice)
