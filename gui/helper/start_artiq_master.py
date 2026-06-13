import json
import os
import subprocess

settings = json.load(open("settings.json"))
cratePath = settings["cratePath"]
config = json.load(open(cratePath + "/config.json"))

condaPath = settings["anacondaPath"]
if not os.path.exists(condaPath + "/Scripts/activate.bat"):
    raise Exception("conda activate script not found in " + condaPath + "/Scripts/activate.bat")
commands = [
    condaPath + "/Scripts/activate.bat",
    condaPath,
    "&&",
    "activate",
    config["ArtiqEnvName"],
    "&&",
    "cd",
    cratePath,
    "&&",
    "artiq_master",
    "--port-notify",
    str(config["port-notify"]),
    "--port-control",
    str(config["port-control"]),
    "--port-logging",
    str(config["port-logging"]),
    "--port-broadcast",
    str(config["port-broadcast"]),
]
process = subprocess.Popen(commands, stderr=subprocess.DEVNULL)
