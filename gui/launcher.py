import json
import os

import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.default_crate_data
import gui.settings as settings
import gui.widgets.Design as Design

window = None


class Window(Design.DragableWindowDesign, QtW.QMainWindow):
    def __init__(self, app, exit_request, start_gui_event, eventLoop):
        super(Window, self).__init__()
        global window
        window = self
        self.app = app
        self.exit_request = exit_request
        self.start_gui_event = start_gui_event
        self.eventLoop = eventLoop
        self.init_window()

    def init_window(self):
        self.setWindowTitle("Sequence Controller Launcher")
        self.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
        self.setContentsMargins(0, 0, 0, 0)

        self.closeButton = Design.CloseButton()
        self.closeButton.clicked.connect(self.close)

        self.lastCrate = settings.getCratePath()
        self.openLastCrateButton = None
        if self.lastCrate is not None:
            if os.path.isdir(self.lastCrate):
                self.openLastCrateButton = QtW.QPushButton("Open " + self.lastCrate)
                self.openLastCrateButton.clicked.connect(openLastCrate)

        self.browseCrateButton = QtW.QPushButton("Browse Existing Crate ...")
        self.browseCrateButton.clicked.connect(browseCrateWizard)

        # new crate variables
        self.dirPath = settings.getDefaultCratesDir()
        self.deviceDbPath = None
        self.iconPath = os.getcwd() + "/resources/images/default_icon.png"
        self.crateName = "New Crate"

        self.setContentsMargins(0, 0, 0, 0)

        self.headline = QtW.QLabel("Create a new Crate Project")
        self.fontHeadline = QtG.QFont()
        self.fontHeadline.setBold(True)
        self.headline.setFont(self.fontHeadline)

        self.crateNameLineEdit = QtW.QLineEdit(self.crateName)
        self.crateNameLineEdit.textChanged.connect(self.crateNameLineEditChange)

        self.pathLineEdit = QtW.QLineEdit()
        self.pathLineEdit.setReadOnly(True)
        self.pathLineEdit.setMinimumWidth(250)
        self.pathLineEdit.setText(self.dirPath)
        self.pathEditButton = Design.Button(" ... ")
        self.pathEditButton.clicked.connect(self.choseDir)

        self.useTestDeviceDbCheckbox = QtW.QCheckBox()
        self.useTestDeviceDbCheckbox.stateChanged.connect(self.useTestDeviceDbCheckboxChange)

        self.deviceDbPathLineEdit = QtW.QLineEdit()
        self.deviceDbPathLineEdit.setReadOnly(True)
        self.deviceDbPathEditButton = Design.Button(" ... ")
        self.deviceDbPathEditButton.clicked.connect(self.choseDeviceDb)

        self.iconButton = Design.Button(" ... ")
        self.updateIconButton()
        self.iconButton.clicked.connect(self.choseIcon)

        self.newCrateButton = QtW.QPushButton("Create New Crate")
        self.newCrateButton.clicked.connect(self.newCratePressed)
        self.newCrateButton.setEnabled(False)

        self.artiqVersionCombobox = QtW.QComboBox()
        self.artiqVersionCombobox.addItem("6")
        self.artiqVersionCombobox.addItem("7")
        self.artiqVersionCombobox.addItem("8")
        self.artiqVersionCombobox.setCurrentText("8")

        self.setCentralWidget(
            Design.VBox(
                Design.HBox(
                    Design.Spacer(),
                    QtW.QLabel("Sequence Controller Launcher"),
                    Design.Spacer(),
                    self.closeButton,
                    5,
                ),
                (Design.HBox(self.openLastCrateButton, spacing=10, margins=(10, 5, 10, 5)) if self.openLastCrateButton is not None else QtW.QWidget()),
                Design.HBox(self.browseCrateButton, spacing=10, margins=(10, 5, 10, 5)),
                Design.HBox(self.headline, Design.Spacer(), spacing=10, margins=(10, 5, 10, 5)),
                Design.HBox(
                    QtW.QLabel("crate name"),
                    1,
                    self.crateNameLineEdit,
                    spacing=10,
                    margins=(10, 5, 10, 5),
                ),
                Design.HBox(
                    QtW.QLabel("directory"),
                    1,
                    self.pathLineEdit,
                    self.pathEditButton,
                    spacing=10,
                    margins=(10, 5, 10, 5),
                ),
                Design.HBox(
                    QtW.QLabel("use test device_db.py"),
                    self.useTestDeviceDbCheckbox,
                    Design.Spacer(),
                    spacing=10,
                    margins=(10, 5, 10, 5),
                ),
                Design.HBox(
                    QtW.QLabel("import device_db.py"),
                    1,
                    self.deviceDbPathLineEdit,
                    self.deviceDbPathEditButton,
                    spacing=10,
                    margins=(10, 5, 10, 5),
                ),
                Design.HBox(
                    QtW.QLabel("chose icon (optional)"),
                    Design.Spacer(),
                    self.iconButton,
                    spacing=10,
                    margins=(10, 5, 10, 5),
                ),
                Design.HBox(
                    QtW.QLabel("Artiq version"),
                    Design.Spacer(),
                    self.artiqVersionCombobox,
                    spacing=10,
                    margins=(10, 5, 10, 5),
                ),
                Design.HBox(self.newCrateButton, spacing=10, margins=(10, 5, 10, 5)),
            )
        )

        # self.setFixedSize(400, 300)
        self.show()

        if self.lastCrate is not None and not settings.isChangeCrate():
            if os.path.isdir(self.lastCrate):
                openLastCrate()

    def choseDir(self):
        self.dirPath = QtW.QFileDialog.getExistingDirectory(None, "Directory") + "/"
        self.pathLineEdit.setText(self.dirPath + self.crateName)
        self.checkCompletion()

    def crateNameLineEditChange(self):
        self.crateName = self.crateNameLineEdit.text()
        if self.dirPath is not None:
            self.pathLineEdit.setText(self.dirPath + self.crateName)
        self.checkCompletion()

    def useTestDeviceDbCheckboxChange(self):
        if self.useTestDeviceDbCheckbox.isChecked():
            self.deviceDbPath = os.getcwd() + "/resources/test_device_db.py"
            self.deviceDbPathLineEdit.setText(self.deviceDbPath)
            self.deviceDbPathEditButton.setEnabled(False)
        else:
            self.deviceDbPath = None
            self.deviceDbPathLineEdit.setText("")
            self.deviceDbPathEditButton.setEnabled(True)
        self.checkCompletion()

    def choseDeviceDb(self):
        path = QtW.QFileDialog.getOpenFileName(None, "Chose device_db.py", None, "(device_db.py)")[0]
        if len(path) >= 12 and path[-12:] == "device_db.py":
            self.deviceDbPath = path
            self.deviceDbPathLineEdit.setText(path)
        else:
            alert = QtW.QMessageBox()
            alert.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
            alert.setWindowTitle("Error")
            alert.setText("this is not a device_db.py!")
            alert.exec()
        self.checkCompletion()

    def choseIcon(self):
        path = QtW.QFileDialog.getOpenFileName(None, "Cose Icon", None, "Image Files (*.png *.jpg *.gif)")[0]
        if len(path) >= 4 and (path[-4:] == ".png" or path[-4:] == ".jpg" or path[-4:] == ".gif"):
            self.iconPath = path
            self.updateIconButton()
        else:
            alert = QtW.QMessageBox()
            alert.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
            alert.setWindowTitle("Error")
            alert.setText("this is not a *.png, *.jpg or *.gif file!")
            alert.exec()

    def updateIconButton(self):
        if self.iconPath is None:
            self.iconButton.setText(" ... ")
        else:
            self.iconButton.setText("")
            icon = QtG.QIcon(self.iconPath)
            self.iconButton.setIcon(icon)
            self.setWindowIcon(icon)

    def checkCompletion(self):
        if self.dirPath is None or self.deviceDbPath is None or self.crateName == "":
            self.newCrateButton.setEnabled(False)
        else:
            self.newCrateButton.setEnabled(True)

    def newCratePressed(self):
        checkDeviceDbPath = self.dirPath + self.crateName + "/" + "device_db.py"

        crate.FileManager.cratePath = self.dirPath + self.crateName + "/"

        settings.setDefaultCratesDir(self.dirPath)

        try:
            os.mkdir(crate.FileManager.cratePath)
        except FileExistsError:
            pass

        if os.path.isfile(checkDeviceDbPath) and not self.deviceDbPath == checkDeviceDbPath:
            alert = QtW.QMessageBox()
            alert.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
            alert.setWindowTitle("Error")
            alert.setText("this folder already contains a different device_db.py!")
            alert.exec()
            return

        for file in crate.FileManager.FILES.keys():
            if os.path.isfile(self.dirPath + self.crateName + "/" + file):
                alert = QtW.QMessageBox()
                alert.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
                alert.setWindowTitle("Error")
                alert.setText("this folder already contains a " + file + "!")
                alert.exec()
                return

        default_crate_data = gui.default_crate_data.generate(open(self.deviceDbPath).read())
        crate.sequences = default_crate_data["sequences"]
        crate.labsetup = default_crate_data["labsetup"]
        crate.rpcs = default_crate_data["rpcs"]
        crate.variables = default_crate_data["variables"]
        crate.multiruns = default_crate_data["multiruns"]
        crate.config = {
            "artiqVersion": self.artiqVersionCombobox.currentText(),
            "icon": self.iconPath,
            "name": self.crateName,
            "version": crate.Versioneer.VERSION,
        }

        # copy device_db.py into crate dir
        device_db_data = open(self.deviceDbPath).read()
        new_device_db_file = open(crate.FileManager.cratePath + "device_db.py", "w")
        new_device_db_file.write(device_db_data)
        crate.loadDeviceDbVariables(device_db_data)
        settings.setCratePath(crate.FileManager.cratePath)

        crate.FileManager.save()
        crate.FileManager.generateMissingFilesInPath(crate.FileManager.cratePath)

        # start gui
        self.start_gui_event.set()
        self.close()

    def closeEvent(self, event):
        if crate.gui is None:
            self.exit_request.set()
        super().closeEvent(event)


def openLastCrate():
    path = settings.getCratePath()
    if path == "" or path == "/" or path is None:
        return
    crate.FileManager.cratePath = path
    tryLoadThisPath(crate.FileManager.cratePath)


def browseCrateWizard():
    path = QtW.QFileDialog.getExistingDirectory(None, "Crate Directory") + "/"
    if path == "" or path == "/":
        return
    tryLoadThisPath(path)


def tryLoadThisPath(path, generate=False):
    crate.FileManager.generateMissingFilesInPath(path)
    success, return_message = crate.FileManager.load(path)
    if success:
        window.start_gui_event.set()
        window.close()
    else:
        alert = QtW.QMessageBox()
        alert.setWindowFlags(QtC.Qt.WindowType.FramelessWindowHint)
        alert.setWindowTitle("Error")
        if generate:
            alert.setText(return_message)
        else:
            alert.setText(return_message + "\n" + "Do you want to generate the missing files using default values?")
            alert.addButton("Yes", QtW.QMessageBox.ButtonRole.YesRole)
            alert.addButton("No", QtW.QMessageBox.ButtonRole.NoRole)
        result = alert.exec()
        if not generate and result == 0:
            tryLoadThisPath(path, generate=True)

