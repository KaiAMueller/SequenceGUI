from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6 import QtWidgets as QtW

from gui.widgets.Stabilizer import set_stabilizer


class UpdateWidget(QtW.QWidget):
    def __init__(self, parent: Optional[QtW.QWidget] = None):
        super().__init__(parent)
        self._path_to_lineedit: Dict[str, QtW.QLineEdit] = {}
        self._rows: Dict[str, Dict[str, Any]] = {}

        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QtW.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._add_parameter_button = QtW.QPushButton("Add Parameter")
        self._add_parameter_button.clicked.connect(self._open_add_parameter_dialog)
        root_layout.addWidget(self._add_parameter_button)

        self._ch0_pid_box = QtW.QGroupBox("CH0 - PID")
        self._ch0_pid_layout = QtW.QGridLayout(self._ch0_pid_box)
        self._ch0_pid_layout.setColumnStretch(1, 1)
        self._ch0_pid_layout.setColumnMinimumWidth(2, 26)
        self._ch0_pid_box.setVisible(False)
        root_layout.addWidget(self._ch0_pid_box)

        self._ch0_gen_box = QtW.QGroupBox("CH0 - Generator")
        self._ch0_gen_layout = QtW.QGridLayout(self._ch0_gen_box)
        self._ch0_gen_layout.setColumnStretch(1, 1)
        self._ch0_gen_layout.setColumnMinimumWidth(2, 26)
        self._ch0_gen_box.setVisible(False)
        root_layout.addWidget(self._ch0_gen_box)

        self._ch1_pid_box = QtW.QGroupBox("CH1 - PID")
        self._ch1_pid_layout = QtW.QGridLayout(self._ch1_pid_box)
        self._ch1_pid_layout.setColumnStretch(1, 1)
        self._ch1_pid_layout.setColumnMinimumWidth(2, 26)
        self._ch1_pid_box.setVisible(False)
        root_layout.addWidget(self._ch1_pid_box)

        self._ch1_gen_box = QtW.QGroupBox("CH1 - Generator")
        self._ch1_gen_layout = QtW.QGridLayout(self._ch1_gen_box)
        self._ch1_gen_layout.setColumnStretch(1, 1)
        self._ch1_gen_layout.setColumnMinimumWidth(2, 26)
        self._ch1_gen_box.setVisible(False)
        root_layout.addWidget(self._ch1_gen_box)

        self._misc_box = QtW.QGroupBox("General")
        self._misc_layout = QtW.QGridLayout(self._misc_box)
        self._misc_layout.setColumnStretch(1, 1)
        self._misc_layout.setColumnMinimumWidth(2, 26)
        self._misc_box.setVisible(False)
        root_layout.addWidget(self._misc_box)

        root_layout.addStretch(1)

    def updates_as_text(self) -> Dict[str, str]:
        return {path: edit.text() for path, edit in self._path_to_lineedit.items()}

    def visible_updates(self) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        for path, edit in self._path_to_lineedit.items():
            if not edit.isVisible():
                continue
            updates[path] = self._coerce_value(path, edit.text())
        return updates

    def _coerce_value(self, path: str, text: str) -> Any:
        default = set_stabilizer.DEFAULT_UDPATES.get(path)
        if default is None:
            return text

        stripped = str(text).strip()
        if isinstance(default, bool):
            s = stripped.lower()
            if s in ("1", "true", "t", "yes", "y", "on"):
                return True
            if s in ("0", "false", "f", "no", "n", "off"):
                return False
            return bool(stripped)

        if isinstance(default, int) and not isinstance(default, bool):
            try:
                return int(stripped, 0)
            except Exception:
                return int(float(stripped))

        if isinstance(default, float):
            try:
                return float(stripped)
            except Exception:
                return float("nan")

        return stripped

    def _open_add_parameter_dialog(self) -> None:
        dialog = QtW.QDialog(self)
        dialog.setWindowTitle("Add Parameter")
        dialog.setModal(True)
        dialog_layout = QtW.QVBoxLayout(dialog)
        dialog.resize(1000, 500)

        inner = QtW.QWidget()
        grid = QtW.QGridLayout(inner)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        columns = [
            ("ch0_pid", "CH0 - PID"),
            ("ch0_gen", "CH0 - Generator"),
            ("ch1_pid", "CH1 - PID"),
            ("ch1_gen", "CH1 - Generator"),
            ("misc", "General"),
        ]

        section_to_vbox: Dict[str, QtW.QVBoxLayout] = {}
        for col, (section, title) in enumerate(columns):
            header = QtW.QLabel(title)
            header.setStyleSheet("font-weight: 600;")
            grid.addWidget(header, 0, col)

            col_widget = QtW.QWidget()
            vbox = QtW.QVBoxLayout(col_widget)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(4)
            grid.addWidget(col_widget, 1, col)
            grid.setColumnStretch(col, 1)
            section_to_vbox[section] = vbox

        def add_path_button(path: str) -> None:
            btn = QtW.QPushButton(path)
            btn.setStyleSheet("text-align: left; padding: 4px 8px;")

            def on_clicked() -> None:
                default_value = set_stabilizer.DEFAULT_UDPATES.get(path)
                self._add_update_row(path, default_value)
                dialog.accept()

            btn.clicked.connect(on_clicked)

            section = self._section_for_path(path)
            target = section_to_vbox.get(section)
            if target is None:
                target = section_to_vbox["misc"]
            target.addWidget(btn)

        for path in sorted(set_stabilizer.DEFAULT_UDPATES.keys()):
            add_path_button(str(path))

        for vbox in section_to_vbox.values():
            vbox.addStretch(1)
        dialog_layout.addWidget(inner)

        dialog.exec()

    def _section_for_path(self, path: str) -> str:
        if "/ch/0/" in path:
            if "/source/" in path:
                return "ch0_gen"
            return "ch0_pid"
        if "/ch/1/" in path:
            if "/source/" in path:
                return "ch1_gen"
            return "ch1_pid"
        return "misc"

    def _add_update_row(self, path: str, default_value: Any) -> None:
        if not path or path in self._path_to_lineedit:
            return

        section = self._section_for_path(path)
        name = path.rstrip("/").split("/")[-1]

        label = QtW.QLabel(name)
        label.setToolTip(path)

        edit = QtW.QLineEdit("" if default_value is None else str(default_value))
        edit.setToolTip(path)
        edit.setMinimumWidth(120)

        delete_btn = QtW.QPushButton("🗑")
        delete_btn.setToolTip("Remove")
        delete_btn.setFixedSize(26, 24)
        delete_btn.setStyleSheet(
            "QPushButton {"
            "background-color: #e74c3c;"
            "color: white;"
            "border: 0px;"
            "border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "background-color: #c0392b;"
            "}"
        )

        def on_delete() -> None:
            self._remove_update_row(path)

        delete_btn.clicked.connect(on_delete)

        self._rows[path] = {
            "section": section,
            "label": label,
            "edit": edit,
            "delete": delete_btn,
        }

        self._path_to_lineedit[path] = edit

        self._rebuild_section(section)

    def _remove_update_row(self, path: str) -> None:
        row = self._rows.pop(path, None)
        self._path_to_lineedit.pop(path, None)
        if not row:
            return

        section = row.get("section")
        for key in ("label", "edit", "delete"):
            w = row.get(key)
            if isinstance(w, QtW.QWidget):
                w.setParent(None)
                w.deleteLater()

        if isinstance(section, str):
            self._rebuild_section(section)

    def _clear_layout(self, layout: QtW.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)

    def _rebuild_section(self, section: str) -> None:
        if section == "ch0_pid":
            box = self._ch0_pid_box
            layout = self._ch0_pid_layout
        elif section == "ch0_gen":
            box = self._ch0_gen_box
            layout = self._ch0_gen_layout
        elif section == "ch1_pid":
            box = self._ch1_pid_box
            layout = self._ch1_pid_layout
        elif section == "ch1_gen":
            box = self._ch1_gen_box
            layout = self._ch1_gen_layout
        else:
            box = self._misc_box
            layout = self._misc_layout
            section = "misc"

        self._clear_layout(layout)

        section_paths = [p for p, r in self._rows.items() if r.get("section") == section]
        for row_idx, path in enumerate(section_paths):
            r = self._rows.get(path, {})
            label = r.get("label")
            edit = r.get("edit")
            delete_btn = r.get("delete")
            if isinstance(label, QtW.QWidget):
                layout.addWidget(label, row_idx, 0)
            if isinstance(edit, QtW.QWidget):
                layout.addWidget(edit, row_idx, 1)
            if isinstance(delete_btn, QtW.QWidget):
                layout.addWidget(delete_btn, row_idx, 2)

        box.setVisible(bool(section_paths))


