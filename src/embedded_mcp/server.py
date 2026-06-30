"""embedded-mcp — Let an AI assistant talk to your microcontroller.

This is a Model Context Protocol (MCP) server. It exposes a handful of tools
that an MCP-capable client (Claude Desktop, Claude Code, etc.) can call to:

  * discover serial ports,
  * read the live serial output of a running firmware,
  * send a command/line to the device and capture the reply,
  * decode a raw register value into its named bit-fields.

The goal is simple: when you are debugging firmware, your AI pair can now *see*
what the board is printing and *poke* it — instead of you copy-pasting the
serial monitor back and forth.

Nothing here is magic. Every tool is a thin, well-documented wrapper around
`pyserial`. Read it top to bottom — it is meant to be understood, not just run.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any

import serial
import serial.tools.list_ports
from mcp.server.fastmcp import FastMCP

# The server name is what shows up in the MCP client's tool list.
mcp = FastMCP("embedded-mcp")

# A small safety cap so a tool call can never hang the client forever.
MAX_READ_SECONDS = 30.0


@mcp.tool()
def list_serial_ports() -> list[dict[str, str]]:
    """List the serial ports currently available on this machine.

    Use this first to find out which port your board is on (e.g. "COM5" on
    Windows, "/dev/ttyACM0" on Linux). The other tools all take a `port`.

    Returns one entry per port with its device name and a human description.
    """
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append(
            {
                "port": p.device,
                "description": p.description or "",
                "hwid": p.hwid or "",
            }
        )
    return ports


@mcp.tool()
def read_serial(port: str, baudrate: int = 115200, seconds: float = 3.0) -> dict[str, Any]:
    """Read whatever the device prints on `port` for `seconds`, then return it.

    This opens the port, listens passively, and gives back everything it saw.
    Great for "what is my firmware logging right now?".

    Args:
        port: Serial port name, e.g. "COM5" or "/dev/ttyACM0".
        baudrate: Bits per second. Must match your firmware (default 115200).
        seconds: How long to listen. Capped at 30s.
    """
    seconds = min(max(seconds, 0.1), MAX_READ_SECONDS)
    try:
        with serial.Serial(port, baudrate, timeout=0.1) as ser:
            deadline = time.monotonic() + seconds
            chunks: list[bytes] = []
            while time.monotonic() < deadline:
                data = ser.read(4096)
                if data:
                    chunks.append(data)
            raw = b"".join(chunks)
    except serial.SerialException as exc:
        return {"ok": False, "error": str(exc), "port": port}

    text = raw.decode("utf-8", errors="replace")
    return {
        "ok": True,
        "port": port,
        "baudrate": baudrate,
        "bytes_read": len(raw),
        "text": text,
    }


@mcp.tool()
def send_command(
    port: str,
    command: str,
    baudrate: int = 115200,
    reply_seconds: float = 1.0,
    line_ending: str = "\n",
) -> dict[str, Any]:
    """Send `command` to the device and capture its reply.

    Writes the command (plus a line ending) to the port, then listens for the
    response for `reply_seconds`. Use this to drive a firmware's command shell
    (CLI over UART) — e.g. send "status" and read what comes back.

    Args:
        port: Serial port name.
        command: The text to send (line ending added automatically).
        baudrate: Bits per second (default 115200).
        reply_seconds: How long to wait for the reply. Capped at 30s.
        line_ending: Appended to the command. "\\n", "\\r\\n" or "" .
    """
    reply_seconds = min(max(reply_seconds, 0.0), MAX_READ_SECONDS)
    try:
        with serial.Serial(port, baudrate, timeout=0.1) as ser:
            ser.reset_input_buffer()
            ser.write((command + line_ending).encode("utf-8"))
            ser.flush()
            deadline = time.monotonic() + reply_seconds
            chunks: list[bytes] = []
            while time.monotonic() < deadline:
                data = ser.read(4096)
                if data:
                    chunks.append(data)
            raw = b"".join(chunks)
    except serial.SerialException as exc:
        return {"ok": False, "error": str(exc), "port": port}

    return {
        "ok": True,
        "port": port,
        "sent": command,
        "reply": raw.decode("utf-8", errors="replace"),
    }


@mcp.tool()
def decode_register(value: int, fields: list[dict[str, Any]], width: int = 32) -> dict[str, Any]:
    """Decode a raw register value into its named bit-fields.

    A constant pain in embedded work: you read a register as `0x4002` and have
    to mentally line it up against the datasheet bit map. This does it for you.

    Args:
        value: The raw register value (e.g. 0x4002).
        fields: A list of field descriptors. Each is either:
                {"name": "EN", "bit": 0}                  -> single bit
                {"name": "PRESC", "msb": 5, "lsb": 2}     -> bit range [msb:lsb]
        width: Register width in bits (8, 16, 32...). Used only for display.

    Returns the binary view plus each field's extracted value.
    """
    decoded = []
    for f in fields:
        name = f.get("name", "?")
        if "bit" in f:
            bit = int(f["bit"])
            extracted = (value >> bit) & 0x1
            decoded.append({"name": name, "bits": f"[{bit}]", "value": extracted})
        else:
            msb, lsb = int(f["msb"]), int(f["lsb"])
            mask = (1 << (msb - lsb + 1)) - 1
            extracted = (value >> lsb) & mask
            decoded.append(
                {
                    "name": name,
                    "bits": f"[{msb}:{lsb}]",
                    "value": extracted,
                    "hex": hex(extracted),
                }
            )
    return {
        "value": value,
        "hex": f"0x{value:0{width // 4}X}",
        "binary": format(value, f"0{width}b"),
        "width": width,
        "fields": decoded,
    }


def _svd_fields(svd_path: str, peripheral: str, register: str) -> list[dict[str, Any]]:
    """Pull a register's bit-fields out of a CMSIS-SVD file.

    SVD is the XML chip-description format vendors ship (ST, Nordic, etc.). Each
    field has a name and a position given either as bitOffset+bitWidth or as a
    bitRange like "[5:2]". We normalise both to {name, msb, lsb}.
    """
    root = ET.parse(svd_path).getroot()

    def _find(parent, tag, name):
        for el in parent.iter(tag):
            n = el.findtext("name")
            if n and n.upper() == name.upper():
                return el
        return None

    periph = _find(root, "peripheral", peripheral)
    if periph is None:
        raise ValueError(f"peripheral '{peripheral}' not found in {svd_path}")
    reg = _find(periph, "register", register)
    if reg is None:
        raise ValueError(f"register '{register}' not found in peripheral '{peripheral}'")

    fields: list[dict[str, Any]] = []
    for f in reg.iter("field"):
        name = f.findtext("name") or "?"
        off = f.findtext("bitOffset")
        wid = f.findtext("bitWidth")
        rng = f.findtext("bitRange")
        if off is not None and wid is not None:
            lsb = int(off)
            msb = lsb + int(wid) - 1
        elif rng:  # form: "[msb:lsb]"
            msb, lsb = (int(x) for x in rng.strip("[]").split(":"))
        else:
            continue
        fields.append({"name": name, "msb": msb, "lsb": lsb})
    return fields


@mcp.tool()
def decode_register_svd(
    value: int, svd_path: str, peripheral: str, register: str, width: int = 32
) -> dict[str, Any]:
    """Decode a register by *name* using a CMSIS-SVD chip description file.

    Instead of typing out the bit map by hand (as `decode_register` needs), point
    this at the vendor's `.svd` file and name the peripheral + register. It reads
    the real bit-fields from the SVD and decodes your value against them.

    Example:
        decode_register_svd(0x4002, "STM32F407.svd", "RCC", "CR")

    Args:
        value: The raw register value you read back.
        svd_path: Path to a CMSIS-SVD file on this machine.
        peripheral: Peripheral name as in the SVD, e.g. "RCC".
        register: Register name as in the SVD, e.g. "CR".
        width: Register width in bits for display (default 32).
    """
    try:
        fields = _svd_fields(svd_path, peripheral, register)
    except (ValueError, ET.ParseError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}
    out = decode_register(value, fields, width)
    out["ok"] = True
    out["peripheral"] = peripheral
    out["register"] = register
    return out


def main() -> None:
    """Entry point — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
