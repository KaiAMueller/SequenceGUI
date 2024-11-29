"""
ArtiqGuiSequence Project in PySide6
Started on 2021-07-01
Kai Müller
"""

import asyncio
import atexit
import sys
import traceback
import os

import PySide6.QtWidgets as QtW
import qasync

import gui.artiq_master_manager
import gui.crate
import gui.gui
import gui.launcher
import gui.settings
import gui.widgets.Design as Design

# try:
#     kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
#     process_array = (ctypes.c_uint8 * 1)()
#     num_processes = kernel32.GetConsoleProcessList(process_array, 1)
#     if num_processes < 3:
#         ctypes.WinDLL('user32').ShowWindow(kernel32.GetConsoleWindow(), 0)
# except Exception:
#     pass


def main():
    app = QtW.QApplication(sys.argv)

    eventLoop = qasync.QEventLoop(app)
    asyncio.set_event_loop(eventLoop)
    atexit.register(eventLoop.close)
    launcher_exit_event = asyncio.Event()
    start_gui_event = asyncio.Event()

    gui.settings.loadSettings()

    gui.launcher.Window(app, launcher_exit_event, start_gui_event, eventLoop)
    eventLoop.run_until_complete(launcher_exit_event.wait())

    if not start_gui_event.is_set():
        return

    exit_request = asyncio.Event()
    try:
        gui.artiq_master_manager.start(eventLoop)
    except Exception as e:
        details = str(e) + "\n\n" + traceback.format_exc()
        gui.settings.setChangeCrate(True)
        dialog = Design.DialogDesign("Error")
        errorLog = QtW.QTextEdit(details)
        errorLog.setReadOnly(True)
        errorLog.setFont(Design.SmallValueFont())
        openConfigButton = QtW.QPushButton("Open Config in VS Code")
        configPath = gui.settings.getCratePath() + "/config.json"
        openConfigButton.clicked.connect(lambda: os.system(f"code {configPath}"))
        closeButton = QtW.QPushButton("Close")
        closeButton.clicked.connect(dialog.close)
        dialog.layout().addWidget(Design.VBox(
            QtW.QLabel("Failed to connect to artiq_master. Check Artiq version in config and your artiq environment? 6, 7 and 8 are tested right now.\n\n" + "Error msg: "),
            errorLog,
            Design.HBox(Design.Spacer(), openConfigButton, closeButton))
            )
        dialog.setFixedSize(800, 300)
        dialog.exec()
        return
    gui.crate.gui = gui.gui.Gui(app, eventLoop, exit_request)
    eventLoop.run_until_complete(exit_request.wait())
    gui.artiq_master_manager.kill()


if __name__ == "__main__":
    main()
