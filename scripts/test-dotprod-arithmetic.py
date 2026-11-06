#!/usr/bin/env python3
"""Differential checks for Tcheran's u8 x i8 NNUE first-layer dot product.

The Dotprod implementation uses UDOT(u8, u8) with each signed i8 weight
biased by +128, then subtracts 128 * sum(activations). The baseline NEON
implementation uses signed products plus a 256*w correction for activations
whose high bit is set. Both must match a direct scalar u8*i8 sum exactly.
"""
from __future__ import annotations

import random

SEED = 0x5443484552414E


def dot_scalar(xs: list[int], ws: list[int]) -> int:
    return sum(x * w for x, w in zip(xs, ws, strict=True))


def dot_udot_decomposition(xs: list[int], ws: list[int]) -> int:
    biased_weights = [(w + 128) for w in ws]
    return sum(x * w for x, w in zip(xs, biased_weights, strict=True)) - 128 * sum(xs)


def dot_neon_decomposition(xs: list[int], ws: list[int]) -> int:
    signed_xs = [x if x < 128 else x - 256 for x in xs]
    high_bit = [x >> 7 for x in xs]
    return sum(x * w for x, w in zip(signed_xs, ws, strict=True)) + 256 * sum(
        bit * w for bit, w in zip(high_bit, ws, strict=True)
    )


def check_group(xs: list[int], ws: list[int]) -> None:
    expected = dot_scalar(xs, ws)
    assert dot_udot_decomposition(xs, ws) == expected
    assert dot_neon_decomposition(xs, ws) == expected


def main() -> None:
    # Exhaust every single-byte activation / signed-weight pair.
    for x in range(256):
        for w in range(-128, 128):
            check_group([x], [w])

    rng = random.Random(SEED)
    groups = 250_000
    for _ in range(groups):
        xs = [rng.randrange(256) for _ in range(4)]
        ws = [rng.randrange(-128, 128) for _ in range(4)]
        check_group(xs, ws)

        # Also check the two-vector accumulation used by dpbusdx2.
        xs2 = [rng.randrange(256) for _ in range(4)]
        ws2 = [rng.randrange(-128, 128) for _ in range(4)]
        expected = dot_scalar(xs, ws) + dot_scalar(xs2, ws2)
        assert (
            dot_udot_decomposition(xs, ws)
            + dot_udot_decomposition(xs2, ws2)
            == expected
        )
        assert (
            dot_neon_decomposition(xs, ws)
            + dot_neon_decomposition(xs2, ws2)
            == expected
        )

    print(
        "PASS: 65,536 exhaustive byte/weight pairs + "
        f"{groups:,} randomized 4-byte groups; UDOT and NEON fallback "
        "match scalar u8*i8 arithmetic exactly."
    )


if __name__ == "__main__":
    main()
