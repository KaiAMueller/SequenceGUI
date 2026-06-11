import asyncio
import json
import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Dict, List, Optional


BATCH_SIZE = 8
PAYLOAD_BYTES = 4 * BATCH_SIZE * 2  # adc0, adc1, dac0, dac1 (each i16[BATCH_SIZE])
BYTES_PER_BATCH = PAYLOAD_BYTES


def u16_offset_binary_to_i32(u16: int) -> int:
    return int(u16) - 32768


def unpack_pid_kai_adc_dac_packet(pkt: bytes, payload_offset: int | None = None) -> Dict[str, List[int]]:
    if len(pkt) < PAYLOAD_BYTES:
        raise ValueError(f"packet too short: {len(pkt)} bytes, need at least {PAYLOAD_BYTES}")

    if payload_offset is None:
        payload_offset = len(pkt) - PAYLOAD_BYTES

    payload = pkt[payload_offset : payload_offset + PAYLOAD_BYTES]
    if len(payload) != PAYLOAD_BYTES:
        raise ValueError("bad payload slice")

    fmt_i16 = "<" + ("h" * BATCH_SIZE)
    fmt_u16 = "<" + ("H" * BATCH_SIZE)
    stride = BATCH_SIZE * 2

    adc0 = list(struct.unpack_from(fmt_i16, payload, 0 * stride))
    adc1 = list(struct.unpack_from(fmt_i16, payload, 1 * stride))
    dac0_u = struct.unpack_from(fmt_u16, payload, 2 * stride)
    dac1_u = struct.unpack_from(fmt_u16, payload, 3 * stride)
    dac0 = [u16_offset_binary_to_i32(v) for v in dac0_u]
    dac1 = [u16_offset_binary_to_i32(v) for v in dac1_u]

    return {"adc0": adc0, "adc1": adc1, "dac0": dac0, "dac1": dac1, "payload_offset": payload_offset}


def _decode_one_batch(payload64: bytes) -> Dict[str, List[int]]:
    if len(payload64) != BYTES_PER_BATCH:
        raise ValueError(f"expected {BYTES_PER_BATCH} bytes, got {len(payload64)}")

    fmt_i16 = "<" + ("h" * BATCH_SIZE)
    fmt_u16 = "<" + ("H" * BATCH_SIZE)
    stride = BATCH_SIZE * 2

    adc0 = list(struct.unpack_from(fmt_i16, payload64, 0 * stride))
    adc1 = list(struct.unpack_from(fmt_i16, payload64, 1 * stride))
    dac0_u = struct.unpack_from(fmt_u16, payload64, 2 * stride)
    dac1_u = struct.unpack_from(fmt_u16, payload64, 3 * stride)
    dac0 = [u16_offset_binary_to_i32(v) for v in dac0_u]
    dac1 = [u16_offset_binary_to_i32(v) for v in dac1_u]

    return {"adc0": adc0, "adc1": adc1, "dac0": dac0, "dac1": dac1}


def decode_packet_into_batches(pkt: bytes) -> tuple[int, List[Dict[str, List[int]]]]:
    """Decode a binary UDP datagram containing N packed batches.

    Layout is assumed to be: [header bytes][batch0][batch1]...[batchN-1]
    where each batch is 64 bytes (adc0/adc1/dac0/dac1, each i16[8]).
    Header length is inferred as len(pkt) % 64.
    """
    hdr_len = len(pkt) % BYTES_PER_BATCH
    if len(pkt) < hdr_len + BYTES_PER_BATCH:
        raise ValueError("packet too short")

    payload = pkt[hdr_len:]
    n_batches = len(payload) // BYTES_PER_BATCH
    payload = payload[: n_batches * BYTES_PER_BATCH]

    batches: List[Dict[str, List[int]]] = []
    for i in range(n_batches):
        start = i * BYTES_PER_BATCH
        b = payload[start : start + BYTES_PER_BATCH]
        batches.append(_decode_one_batch(b))
    return hdr_len, batches


def parse_pid_datagram_to_batches(datagram: bytes) -> Optional[List[Dict[str, List[int]]]]:
    """Parse either JSON packets or binary datagrams into a list of batches."""
    try:
        text = datagram.decode("utf-8", errors="strict").strip()
        if text.startswith("{") and text.endswith("}"):
            obj = json.loads(text)
            if isinstance(obj, dict) and "adc0" in obj and "dac0" in obj:
                return [obj]  # type: ignore[list-item]
    except Exception:
        pass

    try:
        _hdr_len, batches = decode_packet_into_batches(datagram)
        return batches
    except Exception:
        return None


@dataclass
class ReceiverState:
    transport: Optional[asyncio.DatagramTransport] = None
    protocol: Optional[asyncio.DatagramProtocol] = None
    is_receiving: bool = False


class UdpReceiverProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_datagram: Callable[[bytes, tuple], None]):
        super().__init__()
        self._on_datagram = on_datagram

    def datagram_received(self, data: bytes, addr):  # type: ignore[override]
        self._on_datagram(data, addr)
