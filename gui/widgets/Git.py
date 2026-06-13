import git
import PySide6.QtCore as QtC
import PySide6.QtGui as QtG
import PySide6.QtWidgets as QtW

import gui.crate as crate
import gui.settings as settings
import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Dock
from gui.widgets.Log import log

dock = None

GIT_IGNORE = """
# Ignore everything
*

# Except these files
!sequences.seq
!labsetup.lab
!variables.json
!multiruns.json
!device_db.py
!config.json
!rpc.json
!scripts
"""


class Dock(gui.widgets.Dock.Dock):
    def __init__(self, gui):
        super(Dock, self).__init__("🚀 Git", gui)
        global dock
        dock = self

        # branch button
        self.branchButton = QtW.QPushButton("No Repo Loaded")
        self.branchButton.clicked.connect(self.branchButtonPressed)

        # commit message line edit
        self.commitLineEdit = QtW.QLineEdit()
        self.commitLineEdit.setPlaceholderText("Commit Message")
        self.commitLineEdit.returnPressed.connect(self.commitButtonPressed)

        # commit button
        self.commitButton = QtW.QPushButton("Commit")
        self.commitButton.clicked.connect(self.commitButtonPressed)

        # commit log table
        self.commitLogTable = CommitLogTable(self)

        # search commit log line edit
        self.commitLogSearch = QtW.QLineEdit()
        self.commitLogSearch.setPlaceholderText("Search Commits")
        self.commitLogSearch.editingFinished.connect(lambda: self.commitLogTable.search(self.commitLogSearch.text()))

        self.loadRepo()

        # set widget
        self.setWidget(
            Design.VBox(
                self.commitLogSearch,
                1,
                self.commitLogTable,
                Design.HBox(
                    "Branch: ",
                    self.branchButton,
                    1,
                    self.commitLineEdit,
                    self.commitButton,
                ),
                margins=(10, 10, 10, 10),
            )
        )

    def loadRepo(self):
        # check if repo exists
        cratePath = settings.getCratePath()
        if cratePath is None:
            return
        try:
            # load repo if exists
            self.repo = git.Repo(cratePath)
            log("Loaded repo at " + self.path())
        except Exception:
            # create repo if doesnt exist
            self.repo = git.Repo.init(cratePath)
            self.commit("First Startup; Initial Commit")
            log("Created repo at " + self.path())

        # create/update gitignore
        with open(self.path() + "/.gitignore", "w") as f:
            f.write(GIT_IGNORE)

        # get branch and set button text
        self.updateBranchButtonText()

        # update commit log
        self.commitLogTable.loadTable(self.repo)

    def path(self):
        return self.repo.working_tree_dir

    def updateBranchButtonText(self):
        branchName = self.getActiveBranchName()
        self.branchButton.setText(branchName if branchName is not None else "DETACHED HEAD")

    def commitButtonPressed(self):

        # commit changes
        self.commit(self.commitLineEdit.text())
        self.commitLineEdit.setText("")

    def commit(self, commit_msg):
        # track files and changes
        self.repo.index.add(self.repo.untracked_files)
        for diff_added in self.repo.index.diff(None):
            self.repo.index.add(diff_added.a_path)

        # commit changes
        self.repo.index.commit(commit_msg)

        # update commit log
        self.commitLogTable.addCommit(self.repo.head.commit)

    def branchButtonPressed(self):
        # create branch button menu
        menu = QtW.QMenu(self)

        # create new branch action
        menu.addAction("New Branch", self.newBranch)

        menu.addSeparator()
        for branch in self.repo.branches:
            # check if branch is active
            if branch.name == self.getActiveBranchName():
                text = "🔴 " + branch.name
            else:
                text = branch.name
            branchMenu = menu.addMenu(text)
            branchMenu.addAction("Checkout", lambda branch=branch: self.checkoutBranch(branch))
            branchMenu.addAction("Rename", lambda branch=branch: self.renameBranch(branch))
            branchMenu.addAction("Delete", lambda branch=branch: self.deleteBranch(branch))

        # show menu
        menu.exec(self.branchButton.mapToGlobal(QtC.QPoint(0, -menu.sizeHint().height())))

    def newBranch(self):
        # get new branch name
        newBranchName = util.textToIdentifier(Design.inputDialog("New Branch", "Enter branch name", ""))
        if newBranchName is None or newBranchName == "":
            return

        if newBranchName in self.repo.branches:
            Design.errorDialog("New Branch", "Branch already exists")
            return

        # create new branch
        self.repo.create_head(newBranchName)
        self.checkoutBranch(self.repo.heads[newBranchName], new=True)

    def renameBranch(self, branch: git.Head):
        newName = util.textToIdentifier(Design.inputDialog("Rename Branch", "Enter new branch name", branch.name))
        if newName is None or newName == "":
            return

        # check if already exists
        if newName in self.repo.branches:
            Design.errorDialog("Rename Branch", f"Branch '{newName}' already exists")
            return

        # rename branch
        branch.rename(newName)
        self.updateBranchButtonText()

    def deleteBranch(self, branch: git.Head):
        # check if branch is active
        if self.getActiveBranchName() == branch.name:
            Design.errorDialog("Delete Branch", "Cannot delete active branch")
            return

        # confirm delete
        if (
            Design.inputDialog(
                "Delete Branch",
                f"Delete branch '{branch.name}'? To confirm please type the name of the branch.",
            )
            != branch.name
        ):
            Design.errorDialog("Delete Branch", "Cancelled deletion.")
            return

        # delete branch
        self.repo.git.branch("-D", branch.name)

        Design.infoDialog("Delete Branch", "Deleted.")

    def getActiveBranchName(self):
        if self.repo.head.is_detached:
            return None
        return self.repo.active_branch.name

    def checkoutBranch(self, branch: git.Head, new=False):
        # check if branch already active
        if branch.name == self.getActiveBranchName():
            return

        if not new:
            confirmationMessage = f"Checkout branch {branch.name}?"
            # check for detached head
            if self.repo.head.is_detached:
                confirmationMessage += """
    WARNING: You are currently on a DETACHED HEAD.
    This means you are not on any branch.
    If you checkout a branch now, you will lose all changes made here on DETACHED HEAD, even if they are commited.
    To save your changes, instead create a new branch from here."""
            # confirm checkout
            if not Design.confirmationDialog("Checkout Branch", confirmationMessage):
                return

        # checkout branch
        self.loadCheckout(branch.name)

        # update branch button text
        self.updateBranchButtonText()

        # update commit log
        self.commitLogTable.loadTable(self.repo)

    def checkoutCommit(self, commitHexsha):
        # get current commit
        currentCommit = self.repo.head.commit

        # check if commit already active
        if currentCommit.hexsha == commitHexsha:
            return

        # confirm checkout
        if not Design.confirmationDialog("Checkout Commit", f"Checkout commit {commitHexsha}?"):
            return

        # checkout commit
        self.loadCheckout(commitHexsha)

        # update commit log
        self.commitLogTable.loadTable(self.repo)

        # update branch button text
        self.updateBranchButtonText()

    def loadCheckout(self, checkoutTarget):
        # save current crate
        crate.FileManager.save()

        # check for untracked changes
        if self.repo.is_dirty():
            if not Design.confirmationDialog(
                "Untracked changes",
                "You have made local changes. Those will be lost if you don't commit them. Are you sure?",
            ):
                return
            # discard local changes
            self.repo.git.reset("--hard")

        # checkout target
        log(f"Checking out {checkoutTarget}")
        try:
            self.repo.git.checkout(checkoutTarget)
        except Exception as e:
            log(e)
            return

        # load crate
        success, return_message = crate.FileManager.load()
        if not success:
            log("Error loading crate:")
            log(return_message)
            return
        crate.gui.loadCrate()


class CommitLogTable(QtW.QTableWidget):
    def __init__(self, dock):
        super(CommitLogTable, self).__init__()
        self.dock = dock
        self.setColumnCount(3)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        # always scroll to bottom
        self.verticalScrollBar().rangeChanged.connect(self.scrollToBottom)

        # set column widths
        self.setColumnWidth(0, 50)
        self.horizontalHeader().setSectionResizeMode(1, QtW.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QtW.QHeaderView.ResizeMode.ResizeToContents)

    def loadTable(self, repo):
        # clear commit log
        self.clear()
        self.setRowCount(0)

        # set column headers
        self.setHorizontalHeaderLabels(["Hash", "Commit Message", "Date"])

        # add commits to commit log
        for commit in reversed(list(repo.iter_commits())):
            self.addCommit(commit)

    def addCommit(self, commit):
        # create table items
        hexshaItem = QtW.QTableWidgetItem(commit.hexsha)
        messageItem = QtW.QTableWidgetItem(commit.message)
        dateItem = QtW.QTableWidgetItem(commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"))

        # add row to table end
        rowCount = self.rowCount()
        self.insertRow(rowCount)
        for i, item in enumerate([hexshaItem, messageItem, dateItem]):
            self.setItem(rowCount, i, item)

    def contextMenuEvent(self, a0: QtG.QContextMenuEvent) -> None:
        # selected entry
        entry = self.itemAt(a0.pos())

        # create context menu
        menu = QtW.QMenu(self)

        # copy entry to clipboard action
        headerLabel = self.horizontalHeaderItem(entry.column()).text()
        menu.addAction(f"Copy {headerLabel} to clipboard", lambda: self.copyEntryToClipboard(entry))

        # checkout commit action
        commitHash = self.item(entry.row(), 0).text()
        menu.addAction("Checkout Commit", lambda: self.dock.checkoutCommit(commitHash))

        # show menu
        menu.exec(a0.globalPos())

    def copyEntryToClipboard(self, entry):
        # copy entry to clipboard
        QtW.QApplication.clipboard().setText(entry.text())

    def search(self, text):
        # show all rows
        for i in range(self.rowCount()):
            self.showRow(i)

        # check if search text is empty
        if text == "":
            return

        # search commit log
        tokens = text.lower().split(" ")
        for i in range(self.rowCount()):
            for token in tokens:
                if token not in self.item(i, 0).text().lower() and token not in self.item(i, 1).text().lower() and token not in self.item(i, 2).text().lower():
                    self.hideRow(i)
                    break
