import copy

import gui.crate as crate
import gui.crate.Actions as Actions

default_config = {
    "ArtiqEnvName": "artiq",
    "port-rpc": 3249,
    "port-notify": 3250,
    "port-control": 3251,
    "port-logging": 1066,
    "port-broadcast": 1067,
    "artiqVersion": "7",
}
locations = {}


def init():
    import gui.widgets.SequenceEditor
    import gui.widgets.TableSequenceView
    import gui.widgets.Git

    global default_config, locations
    default_config[gui.widgets.TableSequenceView.title] = {
        gui.widgets.TableSequenceView.show_all_ports: False,
        gui.widgets.TableSequenceView.expand_subsequences: True,
    }
    default_config[gui.widgets.SequenceEditor.title] = {
        gui.widgets.SequenceEditor.align_ports: True,
        gui.widgets.SequenceEditor.show_full_portnames: False,
        gui.widgets.SequenceEditor.rearrangable_portstates: False,
        gui.widgets.SequenceEditor.enable_big_run_button: True,
    }
    default_config[gui.widgets.Git.title] = {
        gui.widgets.Git.auto_push_on_commit: False,
        gui.widgets.Git.auto_commit_on_run: False,
    }
    locations = {
        gui.widgets.SequenceEditor.title: gui.widgets.SequenceEditor,
        gui.widgets.TableSequenceView.title: gui.widgets.TableSequenceView,
        gui.widgets.Git.title: gui.widgets.Git,
    }


def get(option):
    if option not in crate.config:
        crate.config[option] = copy.deepcopy(default_config[option])
        crate.FileManager.saveConfig()
    return crate.config[option]


def getDockConfig(location, option):
    if location not in crate.config:
        crate.config[location] = {}
    if option not in crate.config[location]:
        crate.config[location][option] = copy.deepcopy(default_config[location][option])
        crate.FileManager.saveConfig()
    return crate.config[location][option]


class ValueChange(Actions.ValueChange):
    def __init__(self, location, option, newValue):
        super(ValueChange, self).__init__(location, option, crate.config[location][option], newValue)

    def description(location, option, oldValue, newValue):
        return f"{location}: Changed {option} from {str(oldValue)} to {str(newValue)}"

    def do(action):
        crate.config[action["name"]][action["valuename"]] = action["newvalue"]
        locations[action["name"]].dock.configChange(action["valuename"], action["newvalue"])
        crate.FileManager.saveConfig()
