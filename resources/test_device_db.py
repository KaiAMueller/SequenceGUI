
# Only for enabling the frontend features in the SequenceGUI, not working with any hardware

device_db = {
    "is_not_real_hardware": {}
}

device_db["urukul0_cpld"] = {
    "module": "artiq.coredevice.urukul",
}

device_db["urukul0_ch0"] = {
    "module": "artiq.coredevice.ad9910",
    "arguments": {
        "cpld_device": "urukul0_cpld"
    }
}

device_db["urukul0_ch1"] = {
    "module": "artiq.coredevice.ad9910",
    "arguments": {
        "cpld_device": "urukul0_cpld",
    }
}

device_db["urukul0_ch2"] = {
    "module": "artiq.coredevice.ad9910",
    "arguments": {
        "cpld_device": "urukul0_cpld",
    }
}

device_db["urukul0_ch3"] = {
    "module": "artiq.coredevice.ad9910",
    "arguments": {
        "cpld_device": "urukul0_cpld",
    }
}

device_db["mirny0_cpld"] = {
    "module": "artiq.coredevice.mirny",
}

device_db["mirny0_ch0"] = {
    "module": "artiq.coredevice.adf5356",
    "arguments": {
        "cpld_device": "mirny0_cpld",
    }
}

device_db["mirny0_ch1"] = {
    "module": "artiq.coredevice.adf5356",
    "arguments": {
        "cpld_device": "mirny0_cpld",
    }
}

device_db["mirny0_ch2"] = {
    "module": "artiq.coredevice.adf5356",
    "arguments": {
        "cpld_device": "mirny0_cpld",
    }
}

device_db["mirny0_ch3"] = {
    "module": "artiq.coredevice.adf5356",
    "arguments": {
        "cpld_device": "mirny0_cpld",
    }
}

device_db["ttl0"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}

device_db["ttl1"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}

device_db["ttl2"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}

device_db["ttl3"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}

device_db["ttl4"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLInOut",
}

device_db["ttl5"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLInOut",
}

device_db["ttl6"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLInOut",
}

device_db["ttl7"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLInOut",
}

device_db["fastino0"] = {
    "module": "artiq.coredevice.fastino",
}

device_db["zotino0"] = {
    "module": "artiq.coredevice.zotino",
}

device_db["led0"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}

device_db["led1"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}

device_db["led2"] = {
    "module": "artiq.coredevice.ttl",
    "class": "TTLOut",
}
