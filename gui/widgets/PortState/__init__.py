import gui.widgets.PortState.DAC as DAC
import gui.widgets.PortState.Mirny as Mirny
import gui.widgets.PortState.Sampler as Sampler
import gui.widgets.PortState.TTL as TTL
import gui.widgets.PortState.Urukul as Urukul

CARD_TYPES = {
    "artiq.coredevice.ttl": TTL,
    "artiq.coredevice.ad9910": Urukul,
    "artiq.coredevice.zotino": DAC,
    "artiq.coredevice.fastino": DAC,
    "artiq.coredevice.sampler": Sampler,
    "artiq.coredevice.adf5356": Mirny,
    "custom.CurrentDriver": DAC,
}

WIDGET_CLASSES = {
    "artiq.coredevice.ttl": TTL.Widget,
    "artiq.coredevice.ad9910": Urukul.Widget,
    "artiq.coredevice.zotino": DAC.Widget,
    "artiq.coredevice.fastino": DAC.Widget,
    "artiq.coredevice.sampler": Sampler.Widget,
    "artiq.coredevice.adf5356": Mirny.Widget,
    "custom.CurrentDriver": DAC.Widget,
}

CONFIG_DIALOG_CLASSES = {
    "artiq.coredevice.ttl": TTL.ConfigDialog,
    "artiq.coredevice.ad9910": Urukul.ConfigDialog,
    "artiq.coredevice.zotino": DAC.ConfigDialog,
    "artiq.coredevice.fastino": DAC.ConfigDialog,
    "artiq.coredevice.sampler": Sampler.ConfigDialog,
    "artiq.coredevice.adf5356": Mirny.ConfigDialog,
    "custom.CurrentDriver": DAC.ConfigDialog,
}
