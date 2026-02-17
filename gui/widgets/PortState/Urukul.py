import PySide6.QtCore as QtC
import PySide6.QtWidgets as QtW

import gui.util as util
import gui.widgets.Design as Design
import gui.widgets.Formula as Formula
import gui.widgets.Input as Input
import gui.widgets.PortState.PortState as PortState
import gui.widgets.Variables as Variables


class Widget(PortState.Widget):
    def __init__(self, segment, portName):
        super(Widget, self).__init__(segment, portName, ConfigDialog)

        # enable switch toggle
        self.configWidgets["switch_enable"] = Input.ToggleButton(
            states=["Set Switch", "Switch"],
            default=self.getValue("switch_enable"),
            changedCallback=self.getChangedCallback("switch_enable"),
        )

        # switch toggle
        self.configWidgets["switch"] = Input.ToggleButton(
            states=["ON", "OFF"],
            default=self.getValue("switch"),
            changedCallback=self.getChangedCallback("switch"),
        )

        # attenuation enable checkbox
        self.configWidgets["attenuation_enable"] = Input.ToggleButton(
            states=["Set Attenuation", "Attenuation"],
            default=self.getValue("attenuation_enable"),
            changedCallback=self.getChangedCallback("attenuation_enable"),
        )

        # attenuation field
        self.configWidgets["attenuation"] = Input.UnitValueField(
            default=self.getValue("attenuation"),
            allowedUnits=[
                {"text": "dB", "factor": 1},
            ],
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("attenuation"),
        )

        # enable frequency update checkbox
        self.configWidgets["mode_enable"] = Input.ToggleButton(
            states=["Set Mode", "Mode"],
            default=self.getValue("mode_enable"),
            changedCallback=self.getChangedCallback("mode_enable"),
        )

        # mode combobox
        self.configWidgets["mode"] = Input.ComboBox(
            itemsGenerateFunction=lambda: [
                "Normal",
                "Sweep frequency",
                "Sweep amplitude",
                "Write RAM Profile",
                "Execute RAM Profile",
            ],
            default=self.getValue("mode"),
            changedCallback=self.getChangedCallback("mode"),
        )

        # ram mode warning label
        self.configWidgets["mode_warning_label"] = QtW.QLabel(
"""Warning: This mode is experimental and may not work as expected.
Always check the output signal before using it in an experiment."""
            )
        self.configWidgets["mode_warning_label"].setObjectName("warning")

        # frequency field
        self.configWidgets["freq_label"] = QtW.QLabel("Frequency")
        self.configWidgets["freq"] = Input.UnitValueField(
            default=self.getValue("freq"),
            allowedUnits=[
                {"text": "kHz", "factor": 1e3},
                {"text": "MHz", "factor": 1e6},
            ],
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("freq"),
        )

        # amplitude field
        self.configWidgets["amp_label"] = QtW.QLabel("Amplitude (0-1.0)")
        self.configWidgets["amp"] = Input.TextField(
            default=self.getValue("amp"),
            reader=float,
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("amp"),
        )

        # phase field
        self.configWidgets["phase_label"] = QtW.QLabel("Phase (0-1.0)")
        self.configWidgets["phase"] = Input.TextField(
            default=self.getValue("phase"),
            reader=float,
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("phase"),
        )

        # sweep frequency field
        self.configWidgets["sweep_freq_label"] = QtW.QLabel("Sweep Frequency")
        self.configWidgets["sweep_freq"] = Input.UnitValueField(
            default=self.getValue("sweep_freq"),
            allowedUnits=[
                {"text": "kHz", "factor": 1e3},
                {"text": "MHz", "factor": 1e6},
            ],
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("sweep_freq"),
        )
        
        # sweep amplitude field
        self.configWidgets["sweep_amp_label"] = QtW.QLabel("Sweep Amplitude")
        self.configWidgets["sweep_amp"] = Input.TextField(
            default=self.getValue("sweep_amp"),
            reader=float,
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("sweep_amp"),
        )
        # enable sweep_duration toggle
        self.configWidgets["sweep_duration_enable"] = Input.ToggleButton(
            states=["Duration", "Set duration"],
            default=self.getValue("sweep_duration_enable"),
            changedCallback=self.getChangedCallback("sweep_duration_enable"),
        )
        
        # sweep duration field
        self.configWidgets["sweep_duration_label"] = QtW.QLabel("Sweep Duration")
        self.configWidgets["sweep_duration"] = Input.UnitValueField(
            default=self.getValue("sweep_duration"),
            allowedUnits=[
                {"text": "s", "factor": 1},
                {"text": "ms", "factor": 1e-3},
                {"text": "us", "factor": 1e-6},
                {"text": "ns", "factor": 1e-9},
            ],
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("sweep_duration"),
        )

        # phase RAM formula
        self.configWidgets["ram_phase_formula_label"] = QtW.QLabel("RAM Phase Formula")
        self.configWidgets["ram_phase_formula"] = Input.FormulaField(
            text="",
            default=self.getValue("ram_phase_formula"),
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("ram_phase_formula"),
        )
        self.configWidgets["ram_phase_formula_selection_button"] = Formula.SelectionButton(text="📚", callback=self.getFormulaChangedCallback("ram_phase_formula"))

        # amplitude RAM formula
        self.configWidgets["ram_amplitude_formula_label"] = QtW.QLabel("RAM Amplitude Formula")
        self.configWidgets["ram_amplitude_formula"] = Input.FormulaField(
            text="",
            default=self.getValue("ram_amplitude_formula"),
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("ram_amplitude_formula"),
        )
        self.configWidgets["ram_amplitude_formula_selection_button"] = Formula.SelectionButton(text="📚", callback=self.getFormulaChangedCallback("ram_amplitude_formula"))

        # frequency RAM formula
        self.configWidgets["ram_frequency_formula_label"] = QtW.QLabel("RAM Frequency Formula")
        self.configWidgets["ram_frequency_formula"] = Input.FormulaField(
            text="",
            default=self.getValue("ram_frequency_formula"),
            replacer=Variables.replacer,
            changedCallback=self.getChangedCallback("ram_frequency_formula"),
        )
        self.configWidgets["ram_frequency_formula_selection_button"] = Formula.SelectionButton(text="📚", callback=self.getFormulaChangedCallback("ram_frequency_formula"))

        # ram profile
        self.configWidgets["ram_profile_label"] = QtW.QLabel("RAM Profile")
        self.configWidgets["ram_profile"] = Input.ComboBox(
            itemsGenerateFunction=lambda: ["1", "2", "3", "4", "5", "6", "7"],
            default=self.getValue("ram_profile"),
            changedCallback=self.getChangedCallback("ram_profile"),
        )

        # ram start
        self.configWidgets["ram_start_label"] = QtW.QLabel("RAM Start")
        self.configWidgets["ram_start"] = Input.TextField(
            default=self.getValue("ram_start"),
            reader=lambda x: util.int_range_reader(x, 0, 1023),
            changedCallback=self.getChangedCallback("ram_start"),
        )

        # ram end
        self.configWidgets["ram_end_label"] = QtW.QLabel("RAM End")
        self.configWidgets["ram_end"] = Input.TextField(
            default=self.getValue("ram_end"),
            reader=lambda x: util.int_range_reader(x, 0, 1023),
            changedCallback=self.getChangedCallback("ram_end"),
        )

        # ram step size
        self.configWidgets["ram_step_size_label"] = QtW.QLabel("RAM Step Size")
        self.configWidgets["ram_step_size"] = Input.TextField(
            default=self.getValue("ram_step_size"),
            reader=int,
            changedCallback=self.getChangedCallback("ram_step_size"),
        )
        self.configWidgets["ram_duration_preview_label"] = QtW.QLabel("")

        # ram destination
        self.configWidgets["ram_destination_label"] = QtW.QLabel("RAM Destination")
        self.configWidgets["ram_destination"] = Input.ComboBox(
            itemsGenerateFunction=lambda: [
                "RAM_DEST_FTW",
                "RAM_DEST_POW",
                "RAM_DEST_ASF",
                "RAM_DEST_POWASF",
            ],
            default=self.getValue("ram_destination"),
            changedCallback=self.getChangedCallback("ram_destination"),
        )

        # ram mode
        self.configWidgets["ram_mode_label"] = QtW.QLabel("RAM Mode")
        self.configWidgets["ram_mode"] = Input.ComboBox(
            itemsGenerateFunction=lambda: [
                "RAM_MODE_DIRECTSWITCH",
                "RAM_MODE_RAMPUP",
                "RAM_MODE_BIDIR_RAMP",
                "RAM_MODE_CONT_BIDIR_RAMP",
                "RAM_MODE_CONT_RAMPUP",
            ],
            default=self.getValue("ram_mode"),
            changedCallback=self.getChangedCallback("ram_mode"),
        )

        self.updatePreviewWidget()
        self.updateRamDurationPreviewLabel()

    def updatePreviewWidget(self):
        self.previewWidget.setText(generatePreviewText(self.getData()))

    def valueChange(self, valueName, newValue):
        super(Widget, self).valueChange(valueName, newValue)
        if valueName in ["switch_enable", "attenuation_enable", "mode_enable", "mode"]:
            self.segment.sequence.alignPorts()
        if valueName in ["ram_start", "ram_end", "ram_step_size"]:
            self.updateRamDurationPreviewLabel()

    def updateRamDurationPreviewLabel(self):
        try:
            start = int(self.getValue("ram_start"))
            end = int(self.getValue("ram_end"))
            step_size = int(self.getValue("ram_step_size"))
            dur = str((end - start + 1) * step_size * 4)  # 4 ns per step
        except Exception:
            dur = "error"
        self.configWidgets["ram_duration_preview_label"].setText(f"RAM Duration: {dur} ns")

    def getTableViewInfo(self):
        return getTableViewInfo(self.getData())


def getTableViewInfo(data):
    tv = {
        "text": generatePreviewText(data, sweep_show="current"),
        "color": (0, 1, 0) if data["switch_enable"] and data["switch"] else (0, 0, 0),
    }
    tv["next_color"] = tv["color"]
    if data["mode"] == "Sweep frequency":
        tv["next_text"] = generatePreviewText(data, sweep_show="next")
    elif data["mode"] == "Sweep amplitude":
        tv["next_text"] = generatePreviewText(data, sweep_show="next")
    else:
        tv["next_text"] = tv["text"]
    return tv


def generatePreviewText(data, sweep_show="all"):
    try:
        switch_enable = data["switch_enable"]
        attenuation_enable = data["attenuation_enable"]
        mode_enable = data["mode_enable"]
        text = ""
        if switch_enable:
            switch = data["switch"]
            text += ("ON" if switch else "OFF") + "\n"
        if attenuation_enable:
            attenuation = data["attenuation"]
            text += util.unitValueToText(attenuation) + "\n"
        if mode_enable:
            mode = data["mode"]
            freq = data["freq"]
            amp = data["amp"]
            if mode == "Normal":
                text += util.unitValueToText(freq) + "\n"
            elif mode == "Sweep frequency":
                sweep_freq = data["sweep_freq"]
                # if Input.getValueFromState(freq, replacer=Variables.replacer) is None or Input.getValueFromState(sweep_freq, replacer=Variables.replacer) is None:
                #     return "error"
                arrow = " ↗ " if Input.getValueFromState(freq, replacer=Variables.replacer) < Input.getValueFromState(sweep_freq, replacer=Variables.replacer) else " ↘ "
                sweep_text_next = util.unitValueToText(sweep_freq) + "\n"
                if freq["unit"] == sweep_freq["unit"]:
                    sweep_text_current = freq["text"] + arrow + "\n"
                else:
                    sweep_text_current = util.unitValueToText(freq) + arrow + "\n"
                text += sweep_text_current if sweep_show == "current" else (sweep_text_next if sweep_show == "next" else (sweep_text_current + sweep_text_next))
            elif mode == "Sweep amplitude":
                sweep_amp = data["sweep_amp"]
                arrow = " ↗ " if Input.getValueFromState(amp, replacer=Variables.replacer) < Input.getValueFromState(sweep_amp, replacer=Variables.replacer) else " ↘ "
                sweep_text_next =  sweep_amp + "\n" + util.unitValueToText(freq) + "\n"
                sweep_text_current =  "Amp \n" + amp + arrow 
                text += sweep_text_current if sweep_show == "current" else (sweep_text_next if sweep_show == "next" else (sweep_text_current + sweep_text_next))
            elif mode == "Execute RAM Profile":
                text += "Exec RAM\n"
            elif mode == "Write RAM Profile":
                text += "Write RAM\n"
            else:
                text += "error\n"
        return text[:-1] if text != "" else "empty"
    except Exception:
        return "error"


class ConfigDialog(PortState.ConfigDialog):
    def __init__(self, portStateWidget):
        super(ConfigDialog, self).__init__(portStateWidget)

    def generateConfigurationWidgets(self):
        return Design.Grid(
            [
                [self.configWidgets["switch_enable"], self.configWidgets["switch"]],
                [
                    self.configWidgets["attenuation_enable"],
                    self.configWidgets["attenuation"],
                ],
                [self.configWidgets["mode_enable"], self.configWidgets["mode"]],
                [QtW.QWidget(), self.configWidgets["mode_warning_label"]],
                [self.configWidgets["freq_label"], self.configWidgets["freq"]],
                [
                    self.configWidgets["sweep_freq_label"],
                    self.configWidgets["sweep_freq"],
                ],
                [self.configWidgets["amp_label"], self.configWidgets["amp"]],
                [
                    self.configWidgets["sweep_amp_label"],
                    self.configWidgets["sweep_amp"],
                ],
                [
                    self.configWidgets["sweep_duration_enable"],
                    self.configWidgets["sweep_duration"],
                ],
                [self.configWidgets["phase_label"], self.configWidgets["phase"]],
                [
                    self.configWidgets["ram_phase_formula_label"],
                    Design.HBox(
                        self.configWidgets["ram_phase_formula"],
                        self.configWidgets["ram_phase_formula_selection_button"],
                    ),
                ],
                [
                    self.configWidgets["ram_amplitude_formula_label"],
                    Design.HBox(
                        self.configWidgets["ram_amplitude_formula"],
                        self.configWidgets["ram_amplitude_formula_selection_button"],
                    ),
                ],
                [
                    self.configWidgets["ram_frequency_formula_label"],
                    Design.HBox(
                        self.configWidgets["ram_frequency_formula"],
                        self.configWidgets["ram_frequency_formula_selection_button"],
                    ),
                ],
                [
                    self.configWidgets["ram_profile_label"],
                    self.configWidgets["ram_profile"],
                ],
                [
                    self.configWidgets["ram_start_label"],
                    self.configWidgets["ram_start"],
                ],
                [self.configWidgets["ram_end_label"], self.configWidgets["ram_end"]],
                [
                    self.configWidgets["ram_step_size_label"],
                    self.configWidgets["ram_step_size"],
                ],
                [self.configWidgets["ram_duration_preview_label"]],
                [
                    self.configWidgets["ram_destination_label"],
                    self.configWidgets["ram_destination"],
                ],
                [self.configWidgets["ram_mode_label"], self.configWidgets["ram_mode"]],
            ],
            alignment=QtC.Qt.AlignmentFlag.AlignLeft,
        )

    def updateVisibility(self):
        if self.isAboutToClose:
            return
        switch_enable = self.configWidgets["switch_enable"].get()
        attenuation_enable = self.configWidgets["attenuation_enable"].get()
        sweep_duration_enable = self.configWidgets["sweep_duration_enable"].get()
        mode_enable = self.configWidgets["mode_enable"].get()
        mode = self.configWidgets["mode"].get()
        ram_destination = self.configWidgets["ram_destination"].get()

        self.configWidgets["switch_enable"].setVisible(True)
        self.configWidgets["attenuation_enable"].setVisible(True)
        self.configWidgets["mode_enable"].setVisible(True)

        self.configWidgets["switch"].setVisible(switch_enable)
        self.configWidgets["attenuation"].setVisible(attenuation_enable)
        self.configWidgets["mode"].setVisible(mode_enable)
        self.configWidgets["mode_warning_label"].setVisible(mode_enable and mode in ["Write RAM Profile", "Execute RAM Profile", "Sweep frequency", "Sweep amplitude"])
        for widget_name in [
            "freq",
            "freq_label",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode not in ["Freq Mod DEMOD", "Execute RAM Profile"] and (mode != "Write RAM Profile" or ram_destination != "RAM_DEST_FTW"))
        self.configWidgets["sweep_freq"].setVisible(mode_enable and mode == "Sweep frequency")
        self.configWidgets["sweep_freq_label"].setVisible(mode_enable and mode == "Sweep frequency")
        self.configWidgets["sweep_duration"].setVisible(sweep_duration_enable and mode_enable and ( mode == "Sweep frequency" or mode == "Sweep amplitude" ))
        self.configWidgets["sweep_duration_enable"].setVisible(mode_enable and ( mode == "Sweep frequency" or mode == "Sweep amplitude" ))
        for widget_name in [
            "amp",
            "amp_label",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode != "Execute RAM Profile" and (mode != "Write RAM Profile" or ram_destination not in ["RAM_DEST_ASF", "RAM_DEST_POWASF"]))
        self.configWidgets["sweep_amp"].setVisible(mode_enable and mode == "Sweep amplitude")
        self.configWidgets["sweep_amp_label"].setVisible(mode_enable and mode == "Sweep amplitude")
        
        self.configWidgets["phase"].setVisible(mode_enable and mode == "Normal")
        self.configWidgets["phase_label"].setVisible(mode_enable and mode == "Normal")
        for widget_name in [
            "ram_phase_formula_label",
            "ram_phase_formula_selection_button",
            "ram_phase_formula",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode == "Write RAM Profile" and ram_destination in ["RAM_DEST_POW", "RAM_DEST_POWASF"])
        for widget_name in [
            "ram_amplitude_formula_label",
            "ram_amplitude_formula_selection_button",
            "ram_amplitude_formula",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode == "Write RAM Profile" and ram_destination in ["RAM_DEST_ASF", "RAM_DEST_POWASF"])
        for widget_name in [
            "ram_frequency_formula_label",
            "ram_frequency_formula_selection_button",
            "ram_frequency_formula",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode == "Write RAM Profile" and ram_destination == "RAM_DEST_FTW")
        for widget_name in [
            "ram_start",
            "ram_start_label",
            "ram_end",
            "ram_end_label",
            "ram_step_size",
            "ram_step_size_label",
            "ram_duration_preview_label",
            "ram_destination",
            "ram_destination_label",
            "ram_mode",
            "ram_mode_label",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode == "Write RAM Profile")
        for widget_name in [
            "ram_profile",
            "ram_profile_label",
        ]:
            self.configWidgets[widget_name].setVisible(mode_enable and mode in ["Write RAM Profile", "Execute RAM Profile"])
