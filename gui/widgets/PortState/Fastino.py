import gui.widgets.PortState.DAC as DAC


class Widget(DAC.Widget):
    def __init__(self, segment, portName):
        super(Widget, self).__init__(segment, portName)
