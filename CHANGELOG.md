# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-06-30

### Added
- Initial release.
- `list_serial_ports` — discover available serial ports.
- `read_serial` — passively read firmware output for N seconds.
- `send_command` — send a line to the device and capture the reply.
- `decode_register` — decode a raw register value into named bit-fields.
- `decode_register_svd` — decode a register *by name* from a CMSIS-SVD file.
- Unit tests and GitHub Actions CI.
- Offline demo (`examples/demo.py`).
