"""Tests for flashing — exercises command building + dry-run, no hardware."""

import pytest

from embedded_mcp.server import _build_flash_command, flash_firmware


def test_st_flash_command():
    cmd = _build_flash_command("st-flash", "fw.bin", address="0x08000000")
    assert cmd == ["st-flash", "write", "fw.bin", "0x08000000"]


def test_probe_rs_with_chip():
    cmd = _build_flash_command("probe-rs", "fw.elf", chip="STM32F407VG")
    assert cmd == ["probe-rs", "download", "--chip", "STM32F407VG", "fw.elf"]


def test_openocd_requires_target():
    with pytest.raises(ValueError):
        _build_flash_command("openocd", "fw.elf")


def test_openocd_command():
    cmd = _build_flash_command("openocd", "fw.elf", openocd_target="target/stm32f4x.cfg")
    assert "program fw.elf verify reset exit" in cmd
    assert cmd[0] == "openocd"


def test_unknown_tool():
    with pytest.raises(ValueError):
        _build_flash_command("nope", "fw.bin")


def test_dry_run_returns_command_without_running():
    out = flash_firmware("fw.bin", tool="st-flash", dry_run=True)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["command"][0] == "st-flash"
