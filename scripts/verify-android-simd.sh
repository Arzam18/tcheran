#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <neon-binary> <dotprod-binary> <llvm-objdump>" >&2
  exit 2
fi

NEON_BIN=$1
DOTPROD_BIN=$2
OBJDUMP=$3

for binary in "$NEON_BIN" "$DOTPROD_BIN"; do
  [[ -s "$binary" ]] || { echo "Missing/empty binary: $binary" >&2; exit 1; }
  "$OBJDUMP" -f "$binary" | grep -q 'aarch64' || {
    echo "Not an AArch64 binary: $binary" >&2
    exit 1
  }
done

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

"$OBJDUMP" -d --mattr=+neon "$NEON_BIN" > "$TMP_DIR/neon.disasm"
"$OBJDUMP" -d --mattr=+dotprod "$DOTPROD_BIN" > "$TMP_DIR/dotprod.disasm"

if grep -Eq '[[:space:]](udot|sdot)[[:space:]]' "$TMP_DIR/neon.disasm"; then
  echo "ERROR: baseline NEON binary contains a Dotprod instruction" >&2
  grep -En '[[:space:]](udot|sdot)[[:space:]]' "$TMP_DIR/neon.disasm" | head -20 >&2
  exit 1
fi

if ! grep -Eq '[[:space:]]udot[[:space:]]' "$TMP_DIR/dotprod.disasm"; then
  echo "ERROR: Dotprod binary does not contain UDOT" >&2
  exit 1
fi

if grep -Eq '[[:space:]]sdot[[:space:]]' "$TMP_DIR/dotprod.disasm"; then
  echo "ERROR: Dotprod binary unexpectedly contains SDOT; expected corrected UDOT path" >&2
  grep -En '[[:space:]]sdot[[:space:]]' "$TMP_DIR/dotprod.disasm" | head -20 >&2
  exit 1
fi

printf 'PASS: baseline is AArch64 NEON without Dotprod; Dotprod binary contains UDOT.\n'
printf 'NEON UDOT/SDOT count: 0\n'
printf 'Dotprod UDOT count: '
grep -Ec '[[:space:]]udot[[:space:]]' "$TMP_DIR/dotprod.disasm"
