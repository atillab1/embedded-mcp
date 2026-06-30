# embedded-mcp

> Let an AI assistant read, command, and debug your microcontroller — over plain serial.

[![CI](https://github.com/atillab1/embedded-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/atillab1/embedded-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-7c3aed.svg)](https://modelcontextprotocol.io/)

**embedded-mcp** is a [Model Context Protocol](https://modelcontextprotocol.io/) server.
It gives an MCP-capable client (Claude Desktop, Claude Code, …) a small set of
tools to talk to a real board over a serial port.

When you debug firmware, your AI pair can now **see what the board prints** and
**poke it back** — instead of you copy-pasting the serial monitor by hand.

```
┌─────────────┐      MCP (stdio)      ┌───────────────┐     UART / USB-serial    ┌──────────────┐
│  AI client  │  ◄────────────────►   │  embedded-mcp │  ◄────────────────────►  │  your board  │
│  (Claude)   │                       │   (this repo) │       (pyserial)         │  STM32 / ...  │
└─────────────┘                       └───────────────┘                          └──────────────┘
```

## Why

Embedded debugging is a loop of *flash → watch the serial monitor → send a
command → read the dump → decode a register against the datasheet*. That loop is
exactly the kind of tedious, context-heavy work an AI is good at — **if you give
it eyes and hands on the hardware.** This server is those eyes and hands.

## Tools

| Tool | What it does |
| --- | --- |
| `list_serial_ports` | Discover available ports (COM5, /dev/ttyACM0, …). |
| `read_serial` | Passively read what the firmware is printing for *N* seconds. |
| `send_command` | Send a line to the device's UART shell and capture the reply. |
| `decode_register` | Turn a raw value (e.g. `0x4002`) into named bit-fields. |
| `decode_register_svd` | Decode a register *by name* straight from a vendor CMSIS-SVD file. |
| `list_flashers` | Report which flashers are installed (st-flash / probe-rs / openocd). |
| `flash_firmware` | Flash a firmware image to the board (dry-run by default). |

## Install

```bash
git clone https://github.com/atillab1/embedded-mcp.git
cd embedded-mcp
pip install -e .
```

## Use with Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "embedded-mcp": {
      "command": "embedded-mcp"
    }
  }
}
```

Restart Claude Desktop. Then just ask:

> *"List my serial ports, then read whatever COM5 is printing at 115200 for 5 seconds."*

> *"Send `status` to the board on COM5 and tell me what it replies."*

> *"Register RCC->CR read back as 0x4002. Decode it: bit 0 is HSION, bit 17 is HSEON, bit 25 is PLLRDY."*

## Example: decode a register

`decode_register(value=0x4002, fields=[{"name":"HSION","bit":0},{"name":"HSEON","bit":17}], width=32)`

```json
{
  "value": 16386,
  "hex": "0x00004002",
  "binary": "00000000000000000100000000000010",
  "fields": [
    { "name": "HSION", "bits": "[0]",  "value": 0 },
    { "name": "HSEON", "bits": "[17]", "value": 0 }
  ]
}
```

## Try it now (no hardware needed)

The register decoders work entirely offline — give them a quick spin:

```bash
python examples/demo.py
```

## Flashing

`flash_firmware` shells out to a real flasher and is **dry-run by default** — it
returns the exact command it *would* run, so you can review it before anything
touches your board:

> *"Dry-run flashing build/app.bin to my STM32 with st-flash."*

Flip `dry_run=False` to actually flash. Supported: `st-flash` (.bin),
`probe-rs` (.elf, needs `chip`), `openocd` (.elf, needs `openocd_target`).

## Safety notes

- Tools open the port only for the duration of the call, then close it — they do
  not hold the port, so your normal IDE serial monitor can share it (one at a time).
- Read durations are capped at 30s so a call can never hang the client.
- `flash_firmware` is destructive; it defaults to a dry run and never flashes
  unless you explicitly pass `dry_run=False`.
- This talks to whatever board is on the port. Don't point it at something you
  don't own.

## Roadmap

- [x] Unit tests + GitHub Actions CI
- [x] Load a register map from an SVD file (`decode_register_svd`)
- [x] Flashing hook (`flash_firmware` via st-flash / probe-rs / openocd)
- [ ] Streaming/continuous monitor (notifications instead of fixed windows)
- [ ] SVD auto-discovery from the connected chip id

Contributions welcome — open an issue or PR.

## Development

```bash
pip install -e .
pip install pytest
pytest -q
```

## License

MIT © Atilla — see [LICENSE](LICENSE).
