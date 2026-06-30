"""Run this with NO hardware to see what embedded-mcp does.

    python examples/demo.py

It exercises the two register-decoding tools exactly the way an AI client would
call them — no board, no serial port required.
"""

import os

from embedded_mcp.server import decode_register, decode_register_svd


def main() -> None:
    print("=== decode_register (manual bit map) ===")
    # STM32 RCC->CR read back as 0x00030083
    out = decode_register(
        0x00030083,
        [
            {"name": "HSION", "bit": 0},
            {"name": "HSIRDY", "bit": 1},
            {"name": "HSEON", "bit": 16},
            {"name": "HSERDY", "bit": 17},
        ],
        width=32,
    )
    print("value :", out["hex"])
    print("binary:", out["binary"])
    for f in out["fields"]:
        print(f"  {f['name']:<8} {f['bits']:<8} = {f['value']}")

    print("\n=== decode_register_svd (names from an SVD file) ===")
    svd = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "sample.svd")
    out = decode_register_svd(0x10001, svd, "RCC", "CR")
    print(f"{out['peripheral']}->{out['register']} =", out["hex"])
    for f in out["fields"]:
        print(f"  {f['name']:<8} {f['bits']:<8} = {f['value']}")


if __name__ == "__main__":
    main()
