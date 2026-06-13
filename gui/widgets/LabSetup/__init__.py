import gui.crate as crate
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.Dock as Dock
import gui.widgets.LabSetup.CurrentDriver as CurrentDriver
import gui.widgets.LabSetup.Fastino as Fastino
import gui.widgets.LabSetup.Mirny as Mirny
import gui.widgets.LabSetup.Sampler as Sampler
import gui.widgets.LabSetup.TTL as TTL
import gui.widgets.LabSetup.Urukul as Urukul
import gui.widgets.LabSetup.Zotino as Zotino
import gui.widgets.TableSequenceView as TableSequenceView
from gui.widgets.Log import log

allowedModuleList = [
    "artiq.coredevice.ttl",
    "artiq.coredevice.ad9910",
    "artiq.coredevice.zotino",
    "artiq.coredevice.fastino",
    "artiq.coredevice.sampler",
    "artiq.coredevice.adf5356",
    "artiq.coredevice.spi2",
]

hasMultipleChannelsModule = [
    "artiq.coredevice.zotino",
    "artiq.coredevice.fastino",
]

DEFAULT_CONFIG_TYPES = {
    "artiq.coredevice.ttl": TTL.Config,
    "artiq.coredevice.zotino": Zotino.Config,
    "artiq.coredevice.fastino": Fastino.Config,
    "artiq.coredevice.ad9910": Urukul.Config,
    "artiq.coredevice.sampler": Sampler.Config,
    "artiq.coredevice.adf5356": Mirny.Config,
}


def getModuleName(device):
    if "module" in crate.device_db[device]:
        module = crate.device_db[device]["module"]
        if module == "artiq.coredevice.spi2" and "CurrentDriver" in device:
            return "custom.CurrentDriver"
        return module
    return None


def widgetClassFromDevice(device):
    if "module" in crate.device_db[device]:
        if crate.device_db[device]["module"] in DEFAULT_CONFIG_TYPES:
            config = DEFAULT_CONFIG_TYPES[crate.device_db[device]["module"]]
            return config
        else:
            if crate.device_db[device]["module"] == "artiq.coredevice.spi2":
                if "CurrentDriver" in device:
                    return CurrentDriver.Config
    return None


def getDevices(portData=None):
    devices = []
    selfitem, modules = None, None
    if portData is not None:
        selfitem = portData["device"]
        modules = [portData["module"]]
        devices.append(selfitem)
    if modules is None:
        modules = allowedModuleList
    loadedDevices = []
    for port in crate.labsetup:
        if not crate.labsetup[port]["isDir"]:
            loadedDevices.append(crate.labsetup[port]["device"])
    for device in crate.device_db:
        if "module" not in crate.device_db[device]:
            continue
        if crate.device_db[device]["module"] not in modules:
            continue
        if (crate.device_db[device]["module"] not in hasMultipleChannelsModule and device in loadedDevices) or selfitem == device:
            continue
        if crate.device_db[device]["module"] == "artiq.coredevice.spi2" and "CurrentDriver" not in device:
            continue
        devices.append(device)
    # remove switches and other ttl stuff for other devices
    for device in crate.device_db:
        if "module" in crate.device_db[device] and "arguments" in crate.device_db[device]:
            for arg in crate.device_db[device]["arguments"].values():
                if type(arg) is str:
                    if arg in devices:
                        devices.remove(arg)
    return devices


dock = None
title = "🔌 Lab Setup"
itemKind = "Port"


class Dock(Dock.ListConfigDockExtension):
    def __init__(self, gui):
        super(Dock, self).__init__(
            title=title,
            gui=gui,
            widgetClass=None,
            itemKind=itemKind,
            backendCallbacks=crate.LabSetup,
            icon="🔌",
        )
        global dock
        dock = self

    def loadCrate(self):
        super(Dock, self).loadCrate(crate.labsetup)

    def addItemButtonClicked(self):
        deviceComboBox = Input.ComboBox(itemsGenerateFunction=getDevices, emptySelectionPossible=True)
        okButton = Design.Button("Ok")
        dialog = Design.DialogDesign("Add Port", "🔌")
        dialog.frameLayout.addWidget(deviceComboBox)
        dialog.frameLayout.addWidget(okButton)
        returnValue = []

        def confirm():
            returnValue.append(deviceComboBox.get())
            dialog.close()

        okButton.clicked.connect(confirm)
        dialog.exec()
        if len(returnValue) == 0 or returnValue[0] == "":
            return None
        device = returnValue[0]
        if device == "" or device is None or device not in crate.device_db:
            return
        portName = util.textToIdentifier(
            Design.inputDialog(
                title=f"{device} name",
                text=f"Enter a name for {device}",
                defaultText=self.generatePortName(device),
            )
        )
        if portName is None or portName == "":
            return None
        if portName in self.list.items:
            Design.errorDialog("Error", f'Port "{portName}" already exists.')
            return None
        portData = {
            "device": device,
            "module": getModuleName(device),
            "isDir": False,
        }
        self.portDataPreProccessing(portData)
        crate.LabSetup.Add(portName, portData)

    def addItem(self, portName, initialLoad=False, isDir=False):
        if isDir:
            super(Dock, self).addItem(portName, initialLoad=initialLoad, isDir=isDir)
            return
        else:
            widgetClass = self.getWidgetClass(portName)
            super(Dock, self).addItem(portName, widgetClass, initialLoad=initialLoad, isDir=isDir)

    def getWidgetClass(self, portName):
        device = crate.labsetup[portName]["device"]
        widgetClass = widgetClassFromDevice(device)
        if widgetClass is None:
            log(f"Error: Device {device} not implemented")
            return
        return widgetClass

    def deletePort(self, portName):
        super(Dock, self).deleteItem(portName)

        # update TableSequenceView
        TableSequenceView.updateTable()

    def renameItem(self, oldName, newName):
        super(Dock, self).renameItem(oldName, newName)

        # update TableSequenceView
        TableSequenceView.updateTable()

    def portDataPreProccessing(self, portData):
        # check if its mirny with almazny
        if portData["module"] == "artiq.coredevice.adf5356":
            portData["hasAlmazny"] = False
            for device in crate.device_db:
                if "class" in crate.device_db[device] and crate.device_db[device]["class"] == "Almazny":
                    if crate.device_db[device]["arguments"]["host_mirny"] == crate.device_db[portData["device"]]["arguments"]["cpld_device"]:
                        portData["hasAlmazny"] = True
                        break

    def generatePortName(self, deviceName):
        newPortName = deviceName
        counter = 1
        while newPortName in crate.labsetup:
            counter += 1
            newPortName = f"{deviceName} ({counter})"
        return newPortName
