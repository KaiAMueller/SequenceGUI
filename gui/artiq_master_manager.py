import atexit
import os
import signal
import socket
import subprocess
import time

import PySide6.QtWidgets as QtW

from sipyco.asyncio_tools import atexit_register_coroutine
from sipyco.broadcast import Receiver
from sipyco.pc_rpc import AsyncioClient, Server, Client
from sipyco.sync_struct import Subscriber

import gui.crate.Config
import gui.settings as settings
import gui.widgets.Log as Log
import gui.widgets.Playlist as Playlist
import gui.widgets.RPC as RPC
from gui.widgets.Log import log

process = None
externalStartedArtiqMaster = False
rpcClient = None
subClient = None
test_mode = False


def start(eventLoop):
    global process
    global externalStartedArtiqMaster
    global rpcClient, subClient
    global test_mode
    cratePath = settings.getCratePath()

    # doesnt work, there must be another way to start artiq_master in wsl. for now has to be started externally
    # crateWslPath = "/mnt/" + cratePath[0].lower() + cratePath[2:]
    # commands = [
    #     "wsl",
    #     "nix", "develop", "~/artiq",
    #     "&&",
    #     "cd", crateWslPath,
    #     "&&",
    #     "artiq_master"
    # ]

    checkTestMode()
    if test_mode:
        return
    
    # check if artiq_master already running
    try:
        testConnection(fast=True)
        externalStartedArtiqMaster = True
    except Exception:
        pass

    checkAndAppendDeviceDbRpcUpdate(externalStartedArtiqMaster)
    process = None
    if not externalStartedArtiqMaster:
        if settings.data["artiqMasterInWsl"]:
            raise Exception("artiq_master needs to be started externally when using wsl setting")
        else:
            condaPath = settings.getAnacondaPath()
            if condaPath is None:
                QtW.QMessageBox.critical(None, "Error", "No running artiq_master found. Close and start one or you can choose a conda installation path to start it automatically.")
                condaPath = settings.choseAnacondaPath()
            if not os.path.exists(condaPath + "/Scripts/activate.bat"):
                raise Exception("conda activate script not found in " + condaPath + "/Scripts/activate.bat")
            commands = [
                condaPath + "/Scripts/activate.bat",
                condaPath,
                "&&",
                "activate",
                settings.getArtiqEnvName(),
                "&&",
                "cd",
                cratePath,
                "&&",
                "artiq_master",
                "--port-notify",
                str(gui.crate.Config.get("port-notify")),
                "--port-control",
                str(gui.crate.Config.get("port-control")),
                "--port-logging",
                str(gui.crate.Config.get("port-logging")),
                "--port-broadcast",
                str(gui.crate.Config.get("port-broadcast")),
            ]
            process = subprocess.Popen(commands, stderr=subprocess.DEVNULL)

        # wait for successfull start
        testConnection()

    # print artiq log in our log
    client = Receiver("log", [], notifyDisconnect)
    eventLoop.run_until_complete(client.connect("127.0.0.1", gui.crate.Config.get("port-broadcast")))
    client.notify_cbs.append(notify)
    atexit_register_coroutine(client.close)

    rpcServer = Server({RPC.device_name: RPC.Server()})
    eventLoop.run_until_complete(rpcServer.start("::1", gui.crate.Config.get("port-rpc")))
    atexit_register_coroutine(rpcServer.stop)

    rpcClient = AsyncioClient()
    target = "master_schedule" if int(gui.crate.Config.get("artiqVersion")) <= 7 else "schedule"
    eventLoop.run_until_complete(rpcClient.connect_rpc("127.0.0.1", gui.crate.Config.get("port-control"), target))
    atexit.register(rpcClient.close_rpc)
    disconnect_reported = False

    def report_disconnect():
        return # false disconnect reports happening...
        nonlocal disconnect_reported
        if not disconnect_reported:
            log(
                "connection to master lost, restart program to reconnect",
                Log.Level.WARNING,
            )
        disconnect_reported = True

    subClient = Subscriber("schedule", lambda x: x, notify_cb=notify_cb, disconnect_cb=report_disconnect)
    eventLoop.run_until_complete(subClient.connect("127.0.0.1", gui.crate.Config.get("port-notify")))
    atexit_register_coroutine(subClient.close)


def notify_cb(data):
    if Playlist.dock is not None:
        Playlist.dock.dataReader.read(data)

def getDeviceDb():
    localdict = {}
    file = open(settings.getCratePath() + "/device_db.py", "r")
    text = file.read()
    file.close()
    exec(text, {}, localdict)
    if "device_db" not in localdict:
        raise Exception("device_db.py did not contain device_db data")
    return localdict["device_db"]

def checkTestMode():
    global test_mode
    device_db = getDeviceDb()
    if "is_not_real_hardware" in device_db:
        test_mode = True
        return

def checkAndAppendDeviceDbRpcUpdate(externalStartedArtiqMaster):
    device_db = getDeviceDb()
    if "sequence_gui_rpc" in device_db:
        port = device_db["sequence_gui_rpc"]["port"]
        if port != gui.crate.Config.get("port-rpc"):
            file = open(settings.getCratePath() + "/device_db.py", "r")
            text = file.read()
            file.close()
            text = text.replace('port": ' + str(port), 'port": ' + str(gui.crate.Config.get("port-rpc")))
            file = open(settings.getCratePath() + "/device_db.py", "w")
            file.write(text)
            file.close()
            if externalStartedArtiqMaster:
                raise Exception("device_db.py was updated, please restart artiq_master")
    else:
        file = open(settings.getCratePath() + "/device_db.py", "a")

        DEVICE_DB_RPC_UPDATE = """
device_db["sequence_gui_rpc"] = {
        "type": "controller",
        "host": "::1",
        "port": PORT-RPC,
}
"""
        DEVICE_DB_RPC_UPDATE = DEVICE_DB_RPC_UPDATE.replace("PORT-RPC", str(gui.crate.Config.get("port-rpc")))
        file.write(DEVICE_DB_RPC_UPDATE)
        file.close()
        if externalStartedArtiqMaster:
            raise Exception("device_db.py was updated, please restart artiq_master")


def testConnection(fast=False):
    for i in range(1 if fast else 3):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("127.0.0.1", gui.crate.Config.get("port-broadcast")))
            s.shutdown(2)
            return
        except Exception:
            pass
        if not fast:
            time.sleep(0.2)
    raise Exception("failed to start Artiq Master")


def notify(message):
    # levels 10-50 from C:\Anaconda3\envs\artiq\Lib\logging\__init__.py
    level = Log.Level.INFO
    if message[0] == 10:
        level = Log.Level.DEBUG
    if message[0] == 20:
        level = Log.Level.INFO
    if message[0] == 30:
        level = Log.Level.WARNING
    if message[0] == 40:
        level = Log.Level.ERROR
    if message[0] == 50:
        level = Log.Level.ERROR
    log("ARTIQ: " + str(message), level)


def notifyDisconnect():
    try:
        log("ARTIQ log disconnected", Log.Level.WARNING)
    except RuntimeError:  # probably because gui already closed
        print("ARTIQ log disconnected")


def kill():
    global process
    if process is not None:
        try:
            master_management = Client("127.0.0.1", gui.crate.Config.get("port-control"), "master_management")
            master_management.terminate()
            master_management.close_rpc()
        except Exception as e:
            print(f"Error: {e}")
            pass
        try:
            process.kill()
        except Exception:
            pass
        process = None
