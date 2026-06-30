"""Tests for decode_register — pure logic, runs without any hardware."""

from embedded_mcp.server import decode_register


def test_single_bits():
    # 0x4002 = bit 1 and bit 14 set.
    out = decode_register(0x4002, [{"name": "EN", "bit": 1}, {"name": "OFF", "bit": 0}], width=16)
    fields = {f["name"]: f["value"] for f in out["fields"]}
    assert fields["EN"] == 1
    assert fields["OFF"] == 0
    assert out["hex"] == "0x4002"


def test_bit_range():
    # bits [5:2] of 0b0000_0000_0011_0100 == 0b1101 == 13
    out = decode_register(0x0034, [{"name": "PRESC", "msb": 5, "lsb": 2}], width=16)
    presc = out["fields"][0]
    assert presc["value"] == 13
    assert presc["bits"] == "[5:2]"


def test_binary_width():
    out = decode_register(0x1, [{"name": "B0", "bit": 0}], width=8)
    assert out["binary"] == "00000001"
    assert len(out["binary"]) == 8
