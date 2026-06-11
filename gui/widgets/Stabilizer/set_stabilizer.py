import pprint

import gui.widgets.RPC
import gui.crate as crate

DEFAULT_UDPATES = {
    "/pid_kai/ch/0/run": True,
    "/pid_kai/ch/1/run": True,
    "/pid_kai/ch/0/gain": 0,
    "/pid_kai/ch/1/gain": 0,
    "/pid_kai/ch/0/pid/in_off": 0.0,
    "/pid_kai/ch/0/pid/out_off": 0.0,
    "/pid_kai/ch/0/pid/p": 0.00,
    "/pid_kai/ch/0/pid/i": 0.00,
    "/pid_kai/ch/0/pid/d": 0.00,
    "/pid_kai/ch/0/pid/min_out": -32768 * 0.5,
    "/pid_kai/ch/0/pid/max_out": 32767 * 0.5,
    "/pid_kai/ch/1/pid/in_off": 0.0,
    "/pid_kai/ch/1/pid/out_off": 0.0,
    "/pid_kai/ch/1/pid/p": 0.00,
    "/pid_kai/ch/1/pid/i": 0.00,
    "/pid_kai/ch/1/pid/d": 0.00,
    "/pid_kai/ch/1/pid/min_out": -32768 * 0.5,
    "/pid_kai/ch/1/pid/max_out": 32767 * 0.5,
    "/pid_kai/stream/ipv4": "192.168.1.50",
    "/pid_kai/stream/port": 2177,

    # --- Signal generator (CH0) ---
    "/pid_kai/ch/0/source/signal": "Cosine",      # or 0..4
    "/pid_kai/ch/0/source/frequency": 100.0,
    "/pid_kai/ch/0/source/symmetry": 0.5,
    "/pid_kai/ch/0/source/amplitude": 1.0,
    "/pid_kai/ch/0/source/offset": 0.0,
    "/pid_kai/ch/0/source/phase": 0.0,
    "/pid_kai/ch/0/source/length": 0,
    "/pid_kai/ch/0/source/state": 0,             # i64 (will be split into LO/HI regs)
    "/pid_kai/ch/0/source/rate": 0,              # i32

    # --- Signal generator (CH1) ---
    "/pid_kai/ch/1/source/signal": "Cosine",
    "/pid_kai/ch/1/source/frequency": 1000.0,
    "/pid_kai/ch/1/source/symmetry": 0.5,
    "/pid_kai/ch/1/source/amplitude": 0.0,
    "/pid_kai/ch/1/source/offset": 0.0,
    "/pid_kai/ch/1/source/phase": 0.0,
    "/pid_kai/ch/1/source/length": 0,
    "/pid_kai/ch/1/source/state": 0,
    "/pid_kai/ch/1/source/rate": 0,

    # IMPORTANT: apply/rebuild generator after changing source settings
    "/pid_kai/trigger": 1,
}


def build_script(stabilizer_device_name, updates, codeID):
    existing_updates: dict = {}
    for path, value in updates.items():
        if path not in DEFAULT_UDPATES:
            raise ValueError(f"Unknown update path: {path}")
        existing_updates[path] = value

    number_value_param = "ndecimals" if int(crate.Config.get("artiqVersion")) <= 7 else "precision"
    updates_literal = pprint.pformat(existing_updates, width=120, sort_dicts=True)

    code_id_argument_line = (
        f'        self.setattr_argument("codeID", NumberValue(type="int", {number_value_param}=0, scale=1, step=1))\n'
    )

    code = '''

from artiq.experiment import *
from artiq.coredevice import spi2 as spi
import struct
import ipaddress

'''
    code += f"STABILIZER_DEVICE_NAME = {stabilizer_device_name!r}\n"
    code += f"UPDATES = {updates_literal}\n\n"
    code += '''
INTER_FRAME_DELAY_US = 200

REG_CH0_GAIN          = 0x0000_0001
REG_CH1_GAIN          = 0x0000_0002
REG_CH0_RUN           = 0x0000_0010
REG_CH1_RUN           = 0x0000_0011
REG_CH0_IN_OFF        = 0x0000_0100
REG_CH0_OUT_OFF       = 0x0000_0101
REG_CH0_P             = 0x0000_0102
REG_CH0_I             = 0x0000_0103
REG_CH0_D             = 0x0000_0104
REG_CH0_MIN_OUT       = 0x0000_0105
REG_CH0_MAX_OUT       = 0x0000_0106
REG_CH1_IN_OFF        = 0x0000_0110
REG_CH1_OUT_OFF       = 0x0000_0111
REG_CH1_P             = 0x0000_0112
REG_CH1_I             = 0x0000_0113
REG_CH1_D             = 0x0000_0114
REG_CH1_MIN_OUT       = 0x0000_0115
REG_CH1_MAX_OUT       = 0x0000_0116
REG_TELEMETRY_PERIOD  = 0x0000_0200
REG_TRIGGER           = 0x0000_0201
REG_STREAM_IPV4       = 0x0000_0300
REG_STREAM_PORT       = 0x0000_0301

# --- Signal generator register map (matches pid-kai.rs) ---
REG_CH0_SRC_SIGNAL    = 0x0000_0400
REG_CH0_SRC_FREQUENCY = 0x0000_0401
REG_CH0_SRC_SYMMETRY  = 0x0000_0402
REG_CH0_SRC_AMPLITUDE = 0x0000_0403
REG_CH0_SRC_OFFSET    = 0x0000_0404
REG_CH0_SRC_PHASE     = 0x0000_0405
REG_CH0_SRC_LENGTH    = 0x0000_0406
REG_CH0_SRC_STATE_LO  = 0x0000_0407
REG_CH0_SRC_STATE_HI  = 0x0000_0408
REG_CH0_SRC_RATE      = 0x0000_0409

REG_CH1_SRC_SIGNAL    = 0x0000_0500
REG_CH1_SRC_FREQUENCY = 0x0000_0501
REG_CH1_SRC_SYMMETRY  = 0x0000_0502
REG_CH1_SRC_AMPLITUDE = 0x0000_0503
REG_CH1_SRC_OFFSET    = 0x0000_0504
REG_CH1_SRC_PHASE     = 0x0000_0505
REG_CH1_SRC_LENGTH    = 0x0000_0506
REG_CH1_SRC_STATE_LO  = 0x0000_0507
REG_CH1_SRC_STATE_HI  = 0x0000_0508
REG_CH1_SRC_RATE      = 0x0000_0509


PATH_TO_REG_KIND = {
    "/pid_kai/ch/0/gain": (REG_CH0_GAIN, "u32"),
    "/pid_kai/ch/1/gain": (REG_CH1_GAIN, "u32"),
    "/pid_kai/ch/0/run": (REG_CH0_RUN, "run"),
    "/pid_kai/ch/1/run": (REG_CH1_RUN, "run"),
    "/pid_kai/ch/0/pid/in_off": (REG_CH0_IN_OFF, "f32"),
    "/pid_kai/ch/0/pid/out_off": (REG_CH0_OUT_OFF, "f32"),
    "/pid_kai/ch/0/pid/p": (REG_CH0_P, "f32"),
    "/pid_kai/ch/0/pid/i": (REG_CH0_I, "f32"),
    "/pid_kai/ch/0/pid/d": (REG_CH0_D, "f32"),
    "/pid_kai/ch/0/pid/min_out": (REG_CH0_MIN_OUT, "f32"),
    "/pid_kai/ch/0/pid/max_out": (REG_CH0_MAX_OUT, "f32"),
    "/pid_kai/ch/1/pid/in_off": (REG_CH1_IN_OFF, "f32"),
    "/pid_kai/ch/1/pid/out_off": (REG_CH1_OUT_OFF, "f32"),
    "/pid_kai/ch/1/pid/p": (REG_CH1_P, "f32"),
    "/pid_kai/ch/1/pid/i": (REG_CH1_I, "f32"),
    "/pid_kai/ch/1/pid/d": (REG_CH1_D, "f32"),
    "/pid_kai/ch/1/pid/min_out": (REG_CH1_MIN_OUT, "f32"),
    "/pid_kai/ch/1/pid/max_out": (REG_CH1_MAX_OUT, "f32"),
    "/pid_kai/telemetry/period": (REG_TELEMETRY_PERIOD, "f32"),
    "/pid_kai/trigger": (REG_TRIGGER, "u32"),
    "/pid_kai/stream/ipv4": (REG_STREAM_IPV4, "ipv4"),
    "/pid_kai/stream/port": (REG_STREAM_PORT, "u32"),

    # --- Source config (CH0) ---
    "/pid_kai/ch/0/source/signal": (REG_CH0_SRC_SIGNAL, "signal"),
    "/pid_kai/ch/0/source/frequency": (REG_CH0_SRC_FREQUENCY, "f32"),
    "/pid_kai/ch/0/source/symmetry": (REG_CH0_SRC_SYMMETRY, "f32"),
    "/pid_kai/ch/0/source/amplitude": (REG_CH0_SRC_AMPLITUDE, "f32"),
    "/pid_kai/ch/0/source/offset": (REG_CH0_SRC_OFFSET, "f32"),
    "/pid_kai/ch/0/source/phase": (REG_CH0_SRC_PHASE, "f32"),
    "/pid_kai/ch/0/source/length": (REG_CH0_SRC_LENGTH, "u32"),
    "/pid_kai/ch/0/source/state": ((REG_CH0_SRC_STATE_LO, REG_CH0_SRC_STATE_HI), "i64"),
    "/pid_kai/ch/0/source/rate": (REG_CH0_SRC_RATE, "i32"),

    # --- Source config (CH1) ---
    "/pid_kai/ch/1/source/signal": (REG_CH1_SRC_SIGNAL, "signal"),
    "/pid_kai/ch/1/source/frequency": (REG_CH1_SRC_FREQUENCY, "f32"),
    "/pid_kai/ch/1/source/symmetry": (REG_CH1_SRC_SYMMETRY, "f32"),
    "/pid_kai/ch/1/source/amplitude": (REG_CH1_SRC_AMPLITUDE, "f32"),
    "/pid_kai/ch/1/source/offset": (REG_CH1_SRC_OFFSET, "f32"),
    "/pid_kai/ch/1/source/phase": (REG_CH1_SRC_PHASE, "f32"),
    "/pid_kai/ch/1/source/length": (REG_CH1_SRC_LENGTH, "u32"),
    "/pid_kai/ch/1/source/state": ((REG_CH1_SRC_STATE_LO, REG_CH1_SRC_STATE_HI), "i64"),
    "/pid_kai/ch/1/source/rate": (REG_CH1_SRC_RATE, "i32"),
}


SPI_MAGIC_REQ = 0xA5
OP_SET = 1

FRAME_SIZE = 16

SPI_FLAGS_BASE = (
    0 * spi.SPI_OFFLINE |
    0 * spi.SPI_CS_POLARITY |
    0 * spi.SPI_CLK_POLARITY |
    0 * spi.SPI_CLK_PHASE |
    0 * spi.SPI_LSB_FIRST |
    0 * spi.SPI_HALF_DUPLEX
)

SPI_LENGTH_BITS = 32
SPI_DIV = 50
SPI_CS = 1


def f32_to_u32(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


def bswap32(x: int) -> int:
    x &= 0xFFFF_FFFF
    return ((x & 0x000000FF) << 24) | ((x & 0x0000FF00) << 8) | ((x & 0x00FF0000) >> 8) | ((x & 0xFF000000) >> 24)


def ipv4_to_u32(v) -> int:
    # Device expects IPv4 in network byte order, but frames pack u32 little-endian.
    # So pre-swap here to avoid 192.168.1.50 -> 50.1.168.192 on device.
    if isinstance(v, int):
        return bswap32(int(v))
    ip = ipaddress.IPv4Address(str(v))
    return bswap32(int(ip))


def signal_to_u32(v) -> int:
    # Must match pid-kai.rs: 0 Cosine, 1 Square, 2 Triangle, 3 WhiteNoise, 4 SweptSine
    if isinstance(v, int):
        return int(v) & 0xFFFF_FFFF
    s = str(v).strip().lower()
    m = {
        "cosine": 0, "cos": 0, "sin": 0,
        "square": 1, "sq": 1,
        "triangle": 2, "tri": 2,
        "whitenoise": 3, "white_noise": 3, "noise": 3,
        "sweptsine": 4, "swept_sine": 4, "sweep": 4,
    }
    if s not in m:
        raise ValueError(f"Invalid signal value: {v!r}")
    return m[s]


def encode_update(kind: str, value):
    """Returns either a u32, or for kind=='i64' returns a (lo_u32, hi_u32) tuple."""
    if kind == "f32":
        return f32_to_u32(value)
    if kind == "ipv4":
        return ipv4_to_u32(value)
    if kind == "signal":
        return signal_to_u32(value)
    if kind == "i32":
        return int(value) & 0xFFFF_FFFF
    if kind == "i64":
        x = int(value)
        x_u64 = x & 0xFFFF_FFFF_FFFF_FFFF
        lo = x_u64 & 0xFFFF_FFFF
        hi = (x_u64 >> 32) & 0xFFFF_FFFF
        return (lo, hi)
    if kind == "run":
        # Firmware enum: 0=Run, 1=Hold, 2=External.
        if isinstance(value, bool):
            return 0 if value else 1
        if isinstance(value, int):
            return int(value) & 0xFFFF_FFFF
        s = str(value).strip().lower()
        if s in ("run", "r", "0"):
            return 0
        if s in ("hold", "h", "1"):
            return 1
        if s in ("external", "ext", "2"):
            return 2
        raise ValueError(f"Invalid run value: {value!r}")
    # default: u32
    return int(value) & 0xFFFF_FFFF


def u32_to_le_bytes(v: int) -> bytes:
    return struct.pack("<I", int(v) & 0xFFFF_FFFF)


def u16_to_le_bytes(v: int) -> bytes:
    return struct.pack("<H", int(v) & 0xFFFF)


def pack_be_u32_from_4bytes(b0, b1, b2, b3) -> int:
    return ((b0 & 0xFF) << 24) | ((b1 & 0xFF) << 16) | ((b2 & 0xFF) << 8) | (b3 & 0xFF)


def build_set_frame(setting_id_u32: int, value_u32: int, seq_u16: int, crc16: int = 0) -> bytes:
    b = bytearray(FRAME_SIZE)
    b[0] = SPI_MAGIC_REQ
    b[1] = OP_SET
    b[4:8] = u32_to_le_bytes(setting_id_u32)
    b[8:12] = u32_to_le_bytes(value_u32)
    b[12:14] = u16_to_le_bytes(seq_u16)
    b[14:16] = u16_to_le_bytes(crc16)
    return bytes(b)


def frame_to_u32_words_for_spi(frame16: bytes):
    assert len(frame16) == 16
    w0 = pack_be_u32_from_4bytes(frame16[0], frame16[1], frame16[2], frame16[3])
    w1 = pack_be_u32_from_4bytes(frame16[4], frame16[5], frame16[6], frame16[7])
    w2 = pack_be_u32_from_4bytes(frame16[8], frame16[9], frame16[10], frame16[11])
    w3 = pack_be_u32_from_4bytes(frame16[12], frame16[13], frame16[14], frame16[15])
    return (w0, w1, w2, w3)


def u32_to_i32(v: int) -> int:
    """Convert 0..0xFFFFFFFF to a signed int32 value (ARTIQ kernel int)."""
    v &= 0xFFFF_FFFF
    return v - 0x1_0000_0000 if (v & 0x8000_0000) else v


'''
    code += f'''
class StabilizerPidKaiSpi(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("{gui.widgets.RPC.device_name}")
'''
    code += code_id_argument_line
    code += '''
        self.setattr_device(STABILIZER_DEVICE_NAME)
        self._spi = getattr(self, STABILIZER_DEVICE_NAME)
        self.kernel_invariants = {"_spi_words", "_spi"}

        self._cfg = []
        for path, value in UPDATES.items():
            if path not in PATH_TO_REG_KIND:
                raise ValueError(f"Unknown update path: {path}")

            reg, kind = PATH_TO_REG_KIND[path]
            encoded = encode_update(kind, value)

            # Support i64 state split into LO/HI registers
            if kind == "i64":
                reg_lo, reg_hi = reg
                lo, hi = encoded
                self._cfg.append((reg_lo, lo))
                self._cfg.append((reg_hi, hi))
            else:
                self._cfg.append((reg, encoded))

        self._spi_words = []
        seq = 1
        for (reg_id, value_u32) in self._cfg:
            frame = build_set_frame(reg_id, int(value_u32) & 0xFFFF_FFFF, seq_u16=seq, crc16=0)
            w0, w1, w2, w3 = frame_to_u32_words_for_spi(frame)
            self._spi_words += [u32_to_i32(w0), u32_to_i32(w1), u32_to_i32(w2), u32_to_i32(w3)]
            seq += 1

    @kernel
    def _spi_write_frame16(self, w0: TInt32, w1: TInt32, w2: TInt32, w3: TInt32):
        self._spi.set_config_mu(SPI_FLAGS_BASE,                SPI_LENGTH_BITS, SPI_DIV, SPI_CS)
        self._spi.write(w0)

        self._spi.set_config_mu(SPI_FLAGS_BASE,                SPI_LENGTH_BITS, SPI_DIV, SPI_CS)
        self._spi.write(w1)

        self._spi.set_config_mu(SPI_FLAGS_BASE,                SPI_LENGTH_BITS, SPI_DIV, SPI_CS)
        self._spi.write(w2)

        self._spi.set_config_mu(SPI_FLAGS_BASE | spi.SPI_END,  SPI_LENGTH_BITS, SPI_DIV, SPI_CS)
        self._spi.write(w3)

'''
    code += f'''
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        self.{gui.widgets.RPC.device_name}.sequenceStarted(\"{codeID}\", \"StabilizerPidKaiSpi\")
        self.core.break_realtime()

        n_frames = len(self._spi_words) // 4
        for i in range(n_frames):
            w0 = self._spi_words[4*i + 0]
            w1 = self._spi_words[4*i + 1]
            w2 = self._spi_words[4*i + 2]
            w3 = self._spi_words[4*i + 3]
            self._spi_write_frame16(w0, w1, w2, w3)
            delay(INTER_FRAME_DELAY_US * us)
            
        delay(5*ms)
        self.core.wait_until_mu(now_mu())
        self.{gui.widgets.RPC.device_name}.sequenceFinished(\"{codeID}\", \"StabilizerPidKaiSpi\")
'''
    return code

