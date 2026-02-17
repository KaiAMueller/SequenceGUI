import json
import os
from pathlib import Path

import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW
import qdarktheme
from playsound import playsound
from PySide6.QtWidgets import QFileDialog

import gui.crate as crate
import gui.widgets.Design as Design
import gui.widgets.Input as Input
import gui.widgets.Log as Log
import gui.widgets.Variables as Variables

data = {}


def loadSettings():
    global data
    try:
        file = open("settings.json", "r")
        data = json.load(file)
    except Exception:
        data = {}
    loadMissingDefaults()
    updateTheme()


def updateTheme():
    try:
        additonal_qss = open("resources/qss_style/normal.qss", "r").read()
        light = open("resources/qss_style/light.qss", "r").read()
        dark = open("resources/qss_style/dark.qss", "r").read()
    except Exception:
        additonal_qss = ""
        light = ""
        dark = ""
    if getDarkmode():
        qdarktheme.setup_theme(additional_qss=additonal_qss + dark)
    else:
        qdarktheme.setup_theme("light", additional_qss=additonal_qss + light)
    Log.updateColors()


def loadMissingDefaults():  # default settings
    if "artiqMasterInWsl" not in data:
        data["artiqMasterInWsl"] = False
    if "darkmode" not in data:
        data["darkmode"] = True
    if "changeCrate" not in data:
        data["changeCrate"] = False
    if "FastinoAfePwrOff" not in data:
        data["FastinoAfePwrOff"] = False
    if "FastinoMaxSamplingRate" not in data:
        data["FastinoMaxSamplingRate"] = {
            "text": "2",
            "unit": {"text": "MS", "factor": 1000000},
        }
    if "FastinoMinTimeStepValue" not in data:
        data["FastinoMinTimeStepValue"] = 0.5e-6
    if "FastinoDelayChannels" not in data:
        data["FastinoDelayChannels"] = {
            "text": "0.05",
            "unit": {"text": "us", "factor": 1e-6},
        }
    if "FastinoDelayChannelsValue" not in data:
        data["FastinoDelayChannelsValue"] = 0.05e-6
    if "FastinoAmountOfSteps" not in data:
        data["FastinoAmountOfSteps"] = {
            "text": "65",
            "unit": {"text": " ", "factor": 1},
        }
    if "FastinoAmountOfStepsValue" not in data:
        data["FastinoAmountOfStepsValue"] = 65
    if "relativeTimestamps" not in data:
        data["relativeTimestamps"] = False
    if "errorSoundOn" not in data:
        data["errorSoundOn"] = True
    if "defaultCratesDir" not in data:
        data["defaultCratesDir"] = str(Path.home()).replace("\\", "/") + "/"
    if "layout" not in data:
        data["layout"] = {
            "maximized": True,
            "tabs": {
                "main": {
                    "docks": [
                        "History",
                        "Playlist",
                        "RPC",
                        "LabSetup",
                        "Log",
                        "Git",
                        "MultiRun",
                        "Variables",
                        "TableSequenceView",
                        "Camera",
                        "Terminal",
                        "SequenceEditor",
                        "Dashboard"
                    ],
                    "state": "000000ff00000000fd000000020000000200000780000001f3fc0100000001fc00000000000007800000028300fffffffc0100000003fb0000001c00530065007100750065006e006300650045006400690074006f007201000000000000048f000000ef00fffffffc000004930000019a000000ac00fffffffa000000000200000002fb00000010004c00610062005300650074007500700100000000000002170000008600fffffffb000000060052005000430100000000ffffffff0000008600fffffffc000006310000014f000000e000fffffffc0200000002fc00000000000000d5000000880100001afa000000000200000003fb00000006004c006f00670100000000000002ab0000006900fffffffb000000100050006c00610079006c0069007300740100000000ffffffff0000006900fffffffb0000000e0048006900730074006f007200790100000000ffffffff0000006d00fffffffb0000000600470069007401000000d90000011a000000b900ffffff0000000300000780000001f3fc0100000006fc000000000000010f0000000000fffffffaffffffff0100000002fb00000010005400650072006d0069006e0061006c0000000000ffffffff0000009200fffffffb0000000c00430061006d0065007200610000000000ffffffff0000013400fffffffb00000012005600610072006900610062006c00650073010000000000000193000000ac00fffffffb00000010004d0075006c0074006900520075006e010000019700000235000000ac00fffffffb00000016004e006500770050006c00610079006c0069007300740100000517000001480000000000000000fb00000022005400610062006c006500530065007100750065006e00630065005600690065007701000003d0000003b0000000cc00fffffffb0000001200440061007300680062006f00610072006400000006bc000000c4000000c400ffffff000007800000000000000004000000040000000800000008fc00000000"
                }
            }
        }
    saveSettings()


def saveSettings():
    if crate.gui is not None:
        layout = {
            "maximized": crate.gui.windows[0].maximized,
            "geometry": crate.gui.windows[0].saveGeometry().data().hex(),
            "tabs": {
                tabName: {
                    "docks": list(tab.getDocks().keys()),
                    "state": tab.saveState().data().hex(),
                }
                for tabName, tab in crate.gui.tabs.items()
            },
        }
        data["layout"] = layout
    try:
        data_json_string = json.dumps(data, indent=4)
        file = open("settings.json", "w")
        file.write(data_json_string)
    except Exception:
        print("Could not save settings.json")


def getAnacondaPath():
    if "anacondaPath" not in data or not os.path.exists(data["anacondaPath"]):
        return None
    return data["anacondaPath"]

def choseAnacondaPath():
    data["anacondaPath"] = QFileDialog.getExistingDirectory(None, "Anaconda/Msys2 Directory Path", str(Path.home()))
    saveSettings()
    return data["anacondaPath"]

def getCratePath():
    if "cratePath" in data:
        return data["cratePath"]
    else:
        return None

def getDefaultCratesDir():
    if "defaultCratesDir" in data:
        return data["defaultCratesDir"]
    else:
        return str(Path.home()).replace("\\", "/") + "/"

def getArtiqEnvName():
    if "ArtiqEnvName" not in crate.config:
        crate.config["ArtiqEnvName"] = Design.inputDialog("ARTIQ environment name", "Enter your ARTIQ's environment name in conda")
    return crate.config["ArtiqEnvName"]


def getDarkmode():
    return data["darkmode"]


def getFastinoAfePwrOff():
    return data["FastinoAfePwrOff"]


def getFastinoMinTimeStep():
    return data["FastinoMinTimeStepValue"]


def getFastinoAmountOfSteps():
    return data["FastinoAmountOfStepsValue"]


def getFastinoDelayChannels():
    return data["FastinoDelayChannelsValue"]


def getRelativeTimestampsEnabled():
    return data["relativeTimestamps"]


def getErrorSoundOn():
    return data["errorSoundOn"]


def setDarkmode(darkmode):
    data["darkmode"] = darkmode
    saveSettings()
    updateTheme()


def setCratePath(path):
    data["cratePath"] = path
    saveSettings()

def setDefaultCratesDir(path):
    data["defaultCratesDir"] = path
    saveSettings()

def getHardwareSetupFilePath():
    return getCratePath() + "HardwareSetup.py"


def setChangeCrate(value=True):
    data["changeCrate"] = value
    saveSettings()


def isChangeCrate():
    return data["changeCrate"]


class Dialog(Design.DialogDesign):
    def __init__(self, gui):
        super().__init__("Settings", "⚙")
        self.gui = gui

        crate.FileManager.complementConfigData()

        self.darkmode = QtW.QCheckBox("Darkmode")
        self.darkmode.setChecked(getDarkmode())
        self.darkmode.stateChanged.connect(self.darkmodeChanged)

        self.artiqMasterInWslCheckbox = QtW.QCheckBox("Artiq Master in WSL (requires restart)")
        self.artiqMasterInWslCheckbox.setChecked(data["artiqMasterInWsl"])
        self.artiqMasterInWslCheckbox.stateChanged.connect(self.artiqMasterInWslChanged)

        self.errorSoundOnCheckbox = QtW.QCheckBox("Error Sound")
        self.errorSoundOnCheckbox.setChecked(data["errorSoundOn"])
        self.errorSoundOnCheckbox.stateChanged.connect(self.errorSoundOnChanged)

        self.guiTab = Design.VBox(
            Design.HBox(self.darkmode, Design.Spacer()),
            Design.HBox(self.artiqMasterInWslCheckbox, Design.Spacer()),
            Design.HBox(self.errorSoundOnCheckbox, Design.Spacer()),
            Design.Spacer(),
            spacing=20,
            margins=(10, 10, 10, 10),
        )

        self.crateNameLineEdit = QtW.QLineEdit(crate.config["name"])
        self.crateNameLineEdit.textChanged.connect(self.crateNameChanged)

        self.iconPathLineEdit = QtW.QLineEdit(crate.config["icon"])
        self.iconPathLineEdit.setReadOnly(True)
        self.iconPathEditButton = Design.Button("")
        if crate.config["icon"] is None or not os.path.isfile(crate.config["icon"]):
            self.iconPathEditButton.setText("📁")
        else:
            icon = QtG.QIcon(crate.config["icon"])
            self.iconPathEditButton.setIcon(icon)
        self.iconPathEditButton.clicked.connect(self.iconPathEditButtonClicked)

        self.ArtiqEnvNameLineEdit = QtW.QLineEdit(crate.config["ArtiqEnvName"])
        self.ArtiqEnvNameLineEdit.textChanged.connect(self.ArtiqEnvNameChanged)

        self.crateTab = Design.VBox(
            Design.HBox(
                QtW.QLabel("ARTIQ env name (requires restart)"),
                1,
                self.ArtiqEnvNameLineEdit,
            ),
            Design.HBox(QtW.QLabel("Crate Name"), 1, self.crateNameLineEdit),
            Design.HBox(
                QtW.QLabel("Icon Path"),
                1,
                self.iconPathLineEdit,
                self.iconPathEditButton,
            ),
            Design.Spacer(),
            spacing=20,
            margins=(10, 10, 10, 10),
        )

        self.FastinoAfePwrOffCheckbox = QtW.QCheckBox("Fastino afe_pwr_off")
        self.FastinoAfePwrOffCheckbox.setChecked(data["FastinoAfePwrOff"])
        self.FastinoAfePwrOffCheckbox.stateChanged.connect(self.FastinoAfePwrOffCheckboxChanged)

        self.FastinoMaxSamplingRate = Input.UnitValueField(
            default=data["FastinoMaxSamplingRate"],
            allowedUnits=[
                {"text": "S", "factor": 1},
                {"text": "kS", "factor": 1e3},
                {"text": "MS", "factor": 1e6},
            ],
            reader=float,
            replacer=Variables.replacer,
            changedCallback=self.FastinoMaxSamplingRateChanged,
            dontUpdateMetrics=False,
            alignment=QtC.Qt.AlignmentFlag.AlignRight,
        )
        self.FastinoDelayChannels = Input.UnitValueField(
            default=data["FastinoDelayChannels"],
            allowedUnits=[
                {"text": "s", "factor": 1},
                {"text": "ms", "factor": 1e-3},
                {"text": "us", "factor": 1e-6},
                {"text": "ns", "factor": 1e-9},
            ],
            reader=float,
            replacer=Variables.replacer,
            changedCallback=self.FastinoDelayChannelsChanged,
            dontUpdateMetrics=False,
            alignment=QtC.Qt.AlignmentFlag.AlignRight,
        )
        self.FastinoAmountOfSteps = Input.UnitValueField(
            default=data["FastinoAmountOfSteps"],
            allowedUnits=[
                {"text": " ", "factor": 1},
                {"text": "k", "factor": 1000},
                {"text": "M", "factor": 1000000},
            ],
            reader=int,
            replacer=Variables.replacer,
            changedCallback=self.FastinoAmountOfStepsChanged,
            dontUpdateMetrics=False,
            alignment=QtC.Qt.AlignmentFlag.AlignRight,
        )

        self.CardsTab = Design.VBox(
            Design.HBox(self.FastinoAfePwrOffCheckbox, Design.Spacer()),
            Design.HBox(
                QtW.QLabel("Sampling rate/s"),
                Design.Spacer(),
                self.FastinoMaxSamplingRate,
            ),
            Design.HBox(
                QtW.QLabel("Delay between channels"),
                Design.Spacer(),
                self.FastinoDelayChannels,
            ),
            Design.HBox(
                QtW.QLabel("Max amount of steps"),
                Design.Spacer(),
                self.FastinoAmountOfSteps,
            ),
            Design.Spacer(),
            spacing=20,
            margins=(10, 10, 10, 10),
        )

        self.relativeTimestampsCheckbox = QtW.QCheckBox("Use Relative Timestamps")
        self.relativeTimestampsCheckbox.setChecked(data["relativeTimestamps"])
        self.relativeTimestampsCheckbox.stateChanged.connect(self.relativeTimestampsCheckboxChanged)

        self.codeGenTab = Design.VBox(
            Design.HBox(self.relativeTimestampsCheckbox, Design.Spacer()),
            Design.Spacer(),
            spacing=20,
            margins=(10, 10, 10, 10),
        )

        self.tabWidget = QtW.QTabWidget()
        self.tabWidget.addTab(self.guiTab, "GUI Settings")
        self.tabWidget.addTab(self.crateTab, "Crate Config")
        self.tabWidget.addTab(self.CardsTab, "Cards Config")
        self.tabWidget.addTab(self.codeGenTab, "Code Generation")
        self.okButton = QtW.QPushButton("Done")
        self.okButton.clicked.connect(self.close)

        self.layout().addWidget(Design.VBox(1, self.tabWidget, self.okButton))

        self.setFixedSize(500, 300)

    def darkmodeChanged(self):
        self.gui.updateAppearance(self.darkmode.isChecked())

    def relativeTimestampsCheckboxChanged(self):
        data["relativeTimestamps"] = self.relativeTimestampsCheckbox.isChecked()
        saveSettings()

    def FastinoAfePwrOffCheckboxChanged(self):
        data["FastinoAfePwrOff"] = self.FastinoAfePwrOffCheckbox.isChecked()
        saveSettings()

    def FastinoMaxSamplingRateChanged(self, getData):
        data["FastinoMaxSamplingRate"] = getData
        data["FastinoMinTimeStepValue"] = 1 / self.FastinoMaxSamplingRate.getValue()
        saveSettings()

    def FastinoDelayChannelsChanged(self, getData):
        data["FastinoDelayChannels"] = getData
        data["FastinoDelayChannelsValue"] = self.FastinoDelayChannels.getValue()
        saveSettings()

    def FastinoAmountOfStepsChanged(self, getData):
        data["FastinoAmountOfSteps"] = getData
        data["FastinoAmountOfStepsValue"] = self.FastinoAmountOfSteps.getValue()
        saveSettings()

    def artiqMasterInWslChanged(self):
        data["artiqMasterInWsl"] = self.artiqMasterInWslCheckbox.isChecked()
        saveSettings()

    def errorSoundOnChanged(self):
        data["errorSoundOn"] = self.errorSoundOnCheckbox.isChecked()
        saveSettings()
        if data["errorSoundOn"]:
            playsound("resources/sounds/error.wav", False)

    def ArtiqEnvNameChanged(self):
        crate.config["ArtiqEnvName"] = self.ArtiqEnvNameLineEdit.text()
        crate.FileManager.saveConfig()

    def crateNameChanged(self):
        crate.config["name"] = self.crateNameLineEdit.text()
        crate.FileManager.saveConfig()

    def iconPathEditButtonClicked(self):
        path = QFileDialog.getOpenFileName(None, "Icon Path", None, "Images (*.png *.jpg *.jpeg *.bmp *.gif)")[0]
        if path != "":
            self.iconPathLineEdit.setText(path)
            crate.config["icon"] = path
            crate.FileManager.saveConfig()
            icon = QtG.QIcon(crate.config["icon"])
            self.iconPathEditButton.setText("")
            self.iconPathEditButton.setIcon(icon)
            self.gui.updateCrateIcon()
