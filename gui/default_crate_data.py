

def generate(deviceDbData):
    ddb_container = {}
    exec(deviceDbData, ddb_container)
    device_db = ddb_container["device_db"]
    data = {
        "sequences": {},
        "labsetup": {},
        "rpcs": {},
        "variables": {},
        "multiruns": {},
    }

    data["rpcs"]["hello_world"] = {
        "isDir": False,
        "file": "hello_world.py",
        "mode": "normal"
    }

    data["variables"]["BlinkTime"] = {
        "isDir": False,
        "value": "500",
        "alias": "BlinkTime"
    }
    data["variables"]["WaitTime"] = {
        "isDir": False,
        "value": "3",
        "alias": "WaitTime"
    }

    data["multiruns"]["ExampleScan"] = {
        "isDir": False,
        "dimensions": {
            "dim0": {
                "variables": {
                    "BlinkTime": {
                        "mode": "linear",
                        "min": "100",
                        "max": "1000",
                        "datalist": []
                    }
                },
                "steps": "10"
            }
        },
        "mode": "scan"
    }

    led_test_port = None
    ttl_test_port = None
    urukul_test_port = None
    mirny_test_port = None
    zotino_test_port = None
    fastino_test_port = None

    for key in device_db:
        if "module" in device_db[key] and device_db[key]["module"] == "artiq.coredevice.ttl":
            if "led" in key:
                data["labsetup"][key] = {
                    "device": key,
                    "module": device_db[key]["module"],
                    "inverted": False,
                    "isDir": False
                }
                if led_test_port is None or key == "led1":
                    led_test_port = key
            elif "urukul" not in key and "mirny" not in key:
                if "TTL" not in data["labsetup"]:
                    data["labsetup"]["TTL"] = {
                        "isDir": True
                    }
                path = f"TTL/{key}"
                data["labsetup"][path] = {
                    "device": key,
                    "module": "artiq.coredevice.ttl",
                    "inverted": False,
                    "isDir": False
                }
                if ttl_test_port is None:
                    ttl_test_port = key
        if "module" in device_db[key] and device_db[key]["module"] in ["artiq.coredevice.ad9910", "artiq.coredevice.adf5356"]:
            if "RF" not in data["labsetup"]:
                data["labsetup"]["RF"] = {
                    "isDir": True
                }
            path = f"RF/{key}"
            data["labsetup"][path] = {
                "device": key,
                "module": device_db[key]["module"],
                "isDir": False
            }
            if urukul_test_port is None and device_db[key]["module"] == "artiq.coredevice.ad9910":
                urukul_test_port = key
            if mirny_test_port is None and device_db[key]["module"] == "artiq.coredevice.adf5356":
                mirny_test_port = key
        if "module" in device_db[key] and device_db[key]["module"] in ["artiq.coredevice.zotino", "artiq.coredevice.fastino"]:
            if "DAC" not in data["labsetup"]:
                data["labsetup"]["DAC"] = {
                    "isDir": True
                }
            for channel in range(32):
                key_ch = f"{key}_ch{channel:02d}"
                path = f"DAC/{key_ch}"
                data["labsetup"][path] = {
                    "device": key,
                    "module": device_db[key]["module"],
                    "isDir": False,
                    "channel": f"{channel}",
                    "calibration_enabled": False,
                    "calibration_unit_text": "nT",
                    "calibration_to_unit": {
                        "text": "V",
                        "factor": 1.0
                    },
                    "calibration_mode": "Formula",
                    "calibration_formula": "x",
                    "calibration_dataset": None,
                }
                if zotino_test_port is None and device_db[key]["module"] == "artiq.coredevice.zotino":
                    zotino_test_port = key_ch
                if fastino_test_port is None and device_db[key]["module"] == "artiq.coredevice.fastino":
                    fastino_test_port = key_ch


    data["sequences"] = {
        "rpc_test": {
            "isDir": False,
            "appearances": {},
            "segments": {
                "segment0": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {},
                    "rpcs": {
                        "hello_world": {
                            "args": "Hello",
                            "kargs": {
                                "World": "123"
                            }
                        }
                    },
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                }
            }
        },
        f"{urukul_test_port}_test": {
            "isDir": False,
            "appearances": {},
            "segments": {
                "segment1": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"RF/{urukul_test_port}": {
                            "switch_enable": True,
                            "switch": True,
                            "attenuation_enable": True,
                            "attenuation": {
                                "text": "10",
                                "unit": {
                                    "text": "dB",
                                    "factor": 1
                                }
                            },
                            "mode_enable": True,
                            "mode": "Normal",
                            "freq": {
                                "text": "100",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "amp": "1.0",
                            "phase": "0.0",
                            "sweep_freq": {
                                "text": "200",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "sweep_duration": {
                                "text": "10",
                                "unit": {
                                    "text": "ms",
                                    "factor": 0.001
                                }
                            },
                            "ram_phase_formula": "0.0",
                            "ram_amplitude_formula": "1.0",
                            "ram_frequency_formula": "1e6",
                            "ram_profile": "1",
                            "ram_start": "0",
                            "ram_end": "1023",
                            "ram_step_size": "16",
                            "ram_destination": "RAM_DEST_POWASF",
                            "ram_mode": "RAM_MODE_RAMPUP"
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                }
            }
        },
        f"{fastino_test_port}_test": {
            "appearances": {},
            "segments": {
                "segment0": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"DAC/{fastino_test_port}": {
                            "voltage": {
                                "text": "0",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": True,
                            "sweep_voltage": {
                                "text": "1000",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": True,
                            "formula_text": "0.42 - 0.5*cos(2*pi*x) + 0.08*cos(4*pi*x)",
                            "formula_selected": "Gauss"
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                }
            },
            "isDir": False
        },
        f"{zotino_test_port}_test": {
            "appearances": {},
            "segments": {
                "segment0": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"DAC/{zotino_test_port}": {
                            "voltage": {
                                "text": "0",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": True,
                            "sweep_voltage": {
                                "text": "1000",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": False,
                            "formula_text": "x"
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "100",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment1": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"DAC/{zotino_test_port}": {
                            "voltage": {
                                "text": "1000",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": True,
                            "sweep_voltage": {
                                "text": "0",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": False,
                            "formula_text": "x"
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "50",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                }
            },
            "isDir": False,
            "pre_compile_rpc": None
        },
        f"{mirny_test_port}_test": {
            "isDir": False,
            "appearances": {},
            "segments": {
                "segment0": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"RF/{mirny_test_port}": {
                            "skipInit": False,
                            "useAlmazny": False,
                            "switch_enable": True,
                            "switch": True,
                            "freq_enable": True,
                            "freq": {
                                "text": "1000",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "attenuation_enable": True,
                            "attenuation": {
                                "text": "10",
                                "unit": {
                                    "text": "dB",
                                    "factor": 1
                                }
                            }
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                }
            }
        },
        f"{led_test_port}_test": {
            "appearances": {
                "_run": [
                    "segment7"
                ]
            },
            "segments": {
                "segment0": {
                    "type": "subsequence",
                    "description": "Subsequence",
                    "enabled": True,
                    "duration": {
                        "text": "1000.000",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    },
                    "subsequence": "led_blink",
                    "repeats": "1"
                },
                "segment1": {
                    "type": "subsequence",
                    "description": "Subsequence",
                    "enabled": True,
                    "duration": {
                        "text": "1000.000",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    },
                    "subsequence": "led_blink",
                    "repeats": "1"
                },
                "segment2": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {},
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "WaitTime",
                        "unit": {
                            "text": "s",
                            "factor": 1
                        }
                    }
                },
                "segment3": {
                    "type": "subsequence",
                    "description": "Subsequence",
                    "enabled": True,
                    "duration": {
                        "text": "1000.000",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    },
                    "subsequence": "led_blink",
                    "repeats": "1"
                }
            },
            "isDir": False,
            "pre_compile_rpc": None,
            "pre_compile_args": ""
        },
        "led_blink": {
            "isDir": False,
            "appearances": {
                f"{led_test_port}_test": [
                    "segment0",
                    "segment1",
                    "segment3"
                ]
            },
            "segments": {
                "segment0": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"{led_test_port}": {
                            "state": True
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "BlinkTime",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment1": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"{led_test_port}": {
                            "state": False
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "BlinkTime",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                }
            }
        },
        "_run": {
            "isDir": False,
            "appearances": {},
            "segments": {
                "segment0": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {},
                    "rpcs": {
                        "hello_world": {
                            "args": "Hello",
                            "kargs": {
                                "World": "123"
                            }
                        }
                    },
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment1": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"DAC/{zotino_test_port}": {
                            "voltage": {
                                "text": "100",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": False,
                            "sweep_voltage": {
                                "text": "200",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": False,
                            "formula_text": "x"
                        },
                        f"TTL/{ttl_test_port}": {
                            "state": True
                        },
                        f"RF/{urukul_test_port}": {
                            "switch_enable": True,
                            "switch": True,
                            "attenuation_enable": False,
                            "attenuation": {
                                "text": "10",
                                "unit": {
                                    "text": "dB",
                                    "factor": 1
                                }
                            },
                            "mode_enable": True,
                            "mode": "Normal",
                            "freq": {
                                "text": "100",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "amp": "1.0",
                            "phase": "0.0",
                            "sweep_freq": {
                                "text": "200",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "sweep_duration": {
                                "text": "10",
                                "unit": {
                                    "text": "ms",
                                    "factor": 0.001
                                }
                            },
                            "ram_phase_formula": "0.0",
                            "ram_amplitude_formula": "1.0",
                            "ram_frequency_formula": "1e6",
                            "ram_profile": "1",
                            "ram_start": "0",
                            "ram_end": "1023",
                            "ram_step_size": "16",
                            "ram_destination": "RAM_DEST_POWASF",
                            "ram_mode": "RAM_MODE_RAMPUP"
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment2": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"TTL/{ttl_test_port}": {
                            "state": False
                        },
                        f"RF/{urukul_test_port}": {
                            "switch_enable": True,
                            "switch": False,
                            "attenuation_enable": False,
                            "attenuation": {
                                "text": "10",
                                "unit": {
                                    "text": "dB",
                                    "factor": 1
                                }
                            },
                            "mode_enable": False,
                            "mode": "Normal",
                            "freq": {
                                "text": "100",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "amp": "1.0",
                            "phase": "0.0",
                            "sweep_freq": {
                                "text": "200",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "sweep_duration": {
                                "text": "10",
                                "unit": {
                                    "text": "ms",
                                    "factor": 0.001
                                }
                            },
                            "ram_phase_formula": "0.0",
                            "ram_amplitude_formula": "1.0",
                            "ram_frequency_formula": "1e6",
                            "ram_profile": "1",
                            "ram_start": "0",
                            "ram_end": "1023",
                            "ram_step_size": "16",
                            "ram_destination": "RAM_DEST_POWASF",
                            "ram_mode": "RAM_MODE_RAMPUP"
                        }
                    },
                    "rpcs": {
                        "logging": {
                            "args": "",
                            "kargs": {}
                        }
                    },
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment3": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"RF/{mirny_test_port}": {
                            "skipInit": False,
                            "useAlmazny": False,
                            "switch_enable": True,
                            "switch": True,
                            "freq_enable": True,
                            "freq": {
                                "text": "1000",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "attenuation_enable": False,
                            "attenuation": {
                                "text": "10",
                                "unit": {
                                    "text": "dB",
                                    "factor": 1
                                }
                            }
                        },
                        f"DAC/{fastino_test_port}": {
                            "voltage": {
                                "text": "100",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": True,
                            "sweep_voltage": {
                                "text": "200",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": False,
                            "formula_text": "x"
                        },
                        f"TTL/{ttl_test_port}": {
                            "state": True
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment4": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"DAC/{zotino_test_port}": {
                            "voltage": {
                                "text": "0",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": False,
                            "sweep_voltage": {
                                "text": "200",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": False,
                            "formula_text": "x"
                        },
                        f"TTL/{ttl_test_port}": {
                            "state": False
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment5": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"RF/{mirny_test_port}": {
                            "skipInit": False,
                            "useAlmazny": False,
                            "switch_enable": True,
                            "switch": False,
                            "freq_enable": False,
                            "freq": {
                                "text": "1000",
                                "unit": {
                                    "text": "MHz",
                                    "factor": 1000000.0
                                }
                            },
                            "attenuation_enable": False,
                            "attenuation": {
                                "text": "10",
                                "unit": {
                                    "text": "dB",
                                    "factor": 1
                                }
                            }
                        },
                        f"DAC/{fastino_test_port}": {
                            "voltage": {
                                "text": "200",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "sweep_enable": True,
                            "sweep_voltage": {
                                "text": "0",
                                "unit": {
                                    "text": "mV",
                                    "factor": 0.001
                                }
                            },
                            "formula_enable": True,
                            "formula_text": "x^2"
                        },
                        f"TTL/{ttl_test_port}": {
                            "state": True
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment6": {
                    "type": "portstate",
                    "description": "Port State",
                    "ports": {
                        f"TTL/{ttl_test_port}": {
                            "state": False
                        }
                    },
                    "rpcs": {},
                    "enabled": True,
                    "duration": {
                        "text": "10",
                        "unit": {
                            "text": "ms",
                            "factor": 0.001
                        }
                    }
                },
                "segment7": {
                    "type": "subsequence",
                    "description": "LED Blinking",
                    "enabled": True,
                    "duration": {
                        "text": "6.0",
                        "unit": {
                            "text": "s",
                            "factor": 1
                        }
                    },
                    "subsequence": f"{led_test_port}_test",
                    "repeats": "1"
                },
            },
            "pre_compile_rpc": None
        }
    }

    # filter all non existing devices from sequences and delete empty sequences
    for sequence in list(data["sequences"]):
        if data["sequences"][sequence]["isDir"]:
            continue
        for segment in list(data["sequences"][sequence]["segments"]):
            if "ports" in data["sequences"][sequence]["segments"][segment]:
                for port in list(data["sequences"][sequence]["segments"][segment]["ports"]):
                    if port not in data["labsetup"]:
                        del data["sequences"][sequence]["segments"][segment]["ports"][port]
                if len(data["sequences"][sequence]["segments"][segment]["ports"]) + len(data["sequences"][sequence]["segments"][segment]["rpcs"]) == 0:
                    del data["sequences"][sequence]["segments"][segment]
        if len(data["sequences"][sequence]["segments"]) == 0:
            clean_up_sequence(data["sequences"], sequence)
    return data

def clean_up_sequence(sequences, sequence):
    if sequences[sequence]["isDir"]:
        return
    for appearance in sequences[sequence]["appearances"]:
        for segment in sequences[sequence]["appearances"][appearance]:
            del sequences[appearance]["segments"][segment]
        if len(sequences[appearance]["segments"]) == 0:
            clean_up_sequence(sequences, appearance)
    del sequences[sequence]
