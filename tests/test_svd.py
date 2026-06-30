"""Tests for SVD-based register decoding — runs without any hardware."""

import os

from embedded_mcp.server import decode_register_svd

SVD = os.path.join(os.path.dirname(__file__), "fixtures", "sample.svd")


def test_decode_from_svd():
    # bit 0 (HSION) and bit 16 (HSEON) set -> 0x10001
    out = decode_register_svd(0x10001, SVD, "RCC", "CR")
    assert out["ok"] is True
    fields = {f["name"]: f["value"] for f in out["fields"]}
    assert fields["HSION"] == 1
    assert fields["HSEON"] == 1
    assert fields["PLLON"] == 0


def test_bitrange_field():
    # HISTRIM is [7:3]; set value 0b10110 (=22) << 3 = 0xB0
    out = decode_register_svd(0xB0, SVD, "RCC", "CR")
    trim = next(f for f in out["fields"] if f["name"] == "HSITRIM")
    assert trim["value"] == 22
    assert trim["bits"] == "[7:3]"


def test_missing_register():
    out = decode_register_svd(0x1, SVD, "RCC", "NOPE")
    assert out["ok"] is False
    assert "not found" in out["error"]
