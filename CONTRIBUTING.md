# Contributing

Thanks for taking a look! This project is small and friendly — issues and PRs
are very welcome, especially:

- New register maps / SVD test fixtures for other chips.
- A streaming monitor tool.
- A flashing hook (`st-flash`, `openocd`, `probe-rs`).

## Setup

```bash
git clone https://github.com/atillab1/embedded-mcp.git
cd embedded-mcp
pip install -e .
pip install pytest
pytest -q
```

## Guidelines

- Keep tools small and well-documented — someone should be able to read a tool
  and understand it without running it.
- Anything that touches a real port must fail gracefully (return an error dict,
  never crash the server).
- Add a test for any logic that can be tested without hardware (the register
  decoders are a good example).
- Run `pytest -q` before opening a PR.

## Reporting bugs

Open an issue with: your OS, Python version, the board/port, and the exact tool
call + what happened vs what you expected.
