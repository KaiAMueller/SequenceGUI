import json
import os
import time
from threading import Thread
from datetime import datetime


import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.settings as settings
from gui.widgets.Log import log

autosaveEvery = 5  # seconds
autosaveLoopThread = None
exitFlag = False

cratePath = None

FILES = {
    "sequences.seq": {"crate_attr": "sequences"},
    "labsetup.lab": {"crate_attr": "labsetup"},
    "config.json": {"crate_attr": "config"},
    "variables.json": {"crate_attr": "variables"},
    "multiruns.json": {"crate_attr": "multiruns"},
    "rpc.json": {"crate_attr": "rpcs"}
}

FOLDERS = {
    "scripts": {},
    "repository": {},
}


def generateMissingFilesInPath(path):
    if not os.path.exists(path):
        os.makedirs(path)
    for fileName in FILES.keys():
        if not os.path.isfile(path + fileName):
            file = open(path + fileName, "w")
            file.write(json.dumps({}, indent=4))
            file.close()
    for folderName in FOLDERS.keys():
        if not os.path.exists(path + folderName):
            os.makedirs(path + folderName)
    if not os.path.isfile(path + "device_db.py"):
        alert = QtW.QMessageBox()
        alert.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
        alert.setWindowTitle("import device_db.py")
        alert.setText("Please browse an existing device_db.py file.")
        alert.exec()
        deviceDbPath = QtW.QFileDialog.getOpenFileName(None, "device_db.py")[0]
        if len(deviceDbPath) >= 12 and deviceDbPath[-12:] == "device_db.py":
            device_db_data = open(deviceDbPath).read()
            file = open(path + "device_db.py", "w")
            file.write(device_db_data)


def load(newCratePath=None):
    if newCratePath is None:
        newCratePath = settings.getCratePath()
    success = True
    return_message = ""
    loadedData = {}
    newDeviceDb = None
    for fileName in FILES.keys():
        try:
            file = open(newCratePath + fileName, "r")
            loadedData[fileName] = json.load(file)
        except OSError:
            success = False
            return_message += f"⚠ no {fileName} file found\n"

    try:
        newDeviceDb = open(newCratePath + "/device_db.py").read()
    except OSError:
        success = False
        return_message += "⚠ no device_db.py file found\n"

    # only if sequences, labsetup, config and device_db all found
    if success:
        global cratePath
        cratePath = newCratePath
        settings.setCratePath(cratePath)
        for fileName, fileInfo in FILES.items():
            setattr(crate, fileInfo["crate_attr"], loadedData[fileName])
        complementConfigData()
        crate.loadDeviceDbVariables(newDeviceDb)
    return success, return_message


def complementConfigData():
    if "name" not in crate.config:
        name = cratePath.split("/")[-2]
        crate.config["name"] = name
    if "ArtiqEnvName" not in crate.config:
        crate.config["ArtiqEnvName"] = "artiq"


def openCrateInFileExplorer():
    if cratePath is None:
        return
    os.startfile(cratePath)


def getScriptsPath():
    return cratePath + "scripts/"


def startAutosaveLoop():
    global autosaveLoopThread
    autosaveLoopThread = Thread(target=autosaveLoop)
    autosaveLoopThread.start()


def joinAutosaveLoop():
    global autosaveLoopThread
    autosaveLoopThread.join()


def autosaveLoop():
    global exitFlag
    i = 0
    while not exitFlag:
        i += 1
        if i >= int(autosaveEvery * 10):
            save()
            i = 0
        time.sleep(0.1)
    save()  # save on exit


def save():
    if cratePath is None:
        return
    for fileName in FILES.keys():
        saveCrateData(fileName)
    settings.saveSettings()


def saveCrateData(fileName):
    fileInfo = FILES[fileName]
    filePath = cratePath + fileName
    try:
        data = json.dumps(getattr(crate, fileInfo["crate_attr"]), indent=4)
        file = open(filePath, "w")
        file.write(data)
        file.close()
    except OSError as e:
        log(e)
        log(f"Error: saving {fileInfo['crate_attr']} to {filePath} failed")

def saveSequenceData(seqName, RID=''):
    try:
        fileInfo = "sequences"
        generatedCodeFolderPath = crate.FileManager.cratePath + "generatedCode/" + datetime.now().strftime("%Y-%m-%d") + "/Sequences" 
        if not os.path.exists(generatedCodeFolderPath):
            os.makedirs(generatedCodeFolderPath)
        seqFilePath = generatedCodeFolderPath + "/" + datetime.now().strftime("%Y%m%d") + "_" + seqName.replace("/", "_") + "_" + f"{RID}" + ".seq"
        data = json.dumps({seqName : getattr(crate, fileInfo)[seqName]}, indent=4)
        file = open(seqFilePath, "w")
        file.write(data)
        file.close()

        
    except OSError as e:
        log(e)
        log(f"Error: saving {fileInfo} to {seqFilePath} failed")
        
    

def saveConfig():
    saveCrateData("config.json")


def saveSequences():
    saveCrateData("sequences.seq")


def saveLabSetup():
    saveCrateData("labsetup.lab")


def saveVariables():
    saveCrateData("variables.json")


def saveMultiRuns():
    saveCrateData("multiruns.json")


def saveRPC():
    saveCrateData("rpc.json")
