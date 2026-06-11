import json
import os
from pathlib import Path
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


def _load_json_with_fallback(file_path, encoding="utf-8"):
    candidates = [
        (file_path, ""),
        (file_path + ".bak", f"⚠ {os.path.basename(file_path)} unreadable; loaded .bak\n"),
        (file_path + ".tmp", f"⚠ {os.path.basename(file_path)} unreadable; loaded .tmp\n"),
    ]

    last_exc = None
    for p, warn in candidates:
        try:
            with open(p, "r", encoding=encoding) as f:
                return json.load(f), warn
        except Exception as e:
            last_exc = e

    raise last_exc


def load(newCratePath=None):
    if newCratePath is None:
        newCratePath = settings.getCratePath()

    success = True
    return_message = ""
    loadedData = {}
    newDeviceDb = None

    for fileName in FILES.keys():
        filePath = _join(newCratePath, fileName)
        try:
            data, warn = _load_json_with_fallback(filePath)
            loadedData[fileName] = data
            if warn:
                return_message += warn
        except OSError:
            success = False
            return_message += f"⚠ no readable {fileName} (or backup) found\n"

    try:
        newDeviceDb = open(_join(newCratePath, "device_db.py"), "r", encoding="utf-8").read()
    except OSError:
        success = False
        return_message += "⚠ no device_db.py file found\n"

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


def _join(*parts):
    return "/".join(p.strip("/\\") for p in parts if p not in (None, ""))

def _fsync_dir(dir_path):
    try:
        fd = os.open(dir_path, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass

def _atomic_write_json(file_path, obj, indent=4, encoding="utf-8", keep_bak=True):
    data = json.dumps(obj, indent=indent)

    tmp_path = file_path + ".tmp"
    bak_path = file_path + ".bak"

    dir_path = os.path.dirname(file_path) or "."
    os.makedirs(dir_path, exist_ok=True)

    with open(tmp_path, "w", encoding=encoding, newline="\n") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    if keep_bak and os.path.exists(file_path):
        try:
            os.replace(file_path, bak_path)
        except OSError:
            pass
    os.replace(tmp_path, file_path)
    _fsync_dir(dir_path)

def saveCrateData(fileName):
    fileInfo = FILES[fileName]
    filePath = _join(cratePath, fileName)
    try:
        obj = getattr(crate, fileInfo["crate_attr"])
        _atomic_write_json(filePath, obj, indent=4, keep_bak=True)
    except (OSError, TypeError, ValueError) as e:
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
