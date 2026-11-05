#!/usr/bin/env python3
"""Copy the boot program (1ST_READ.BIN) off your own disc, for the translator to read.

    python3 scripts/03_get_boot_file.py games/jgr/disc.gdi games/jgr/boot/1ST_READ.BIN

Reads the disc through dcdisc (dream-recomp's disc tool) and checks the result against
data/inputs.sha256. The output folder is ignored by git, and the file is never committed.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BOOT_NAME = "1ST_READ.BIN"
# In a checkout, or in a package's tools folder, where dcdisc and the hash list sit beside this file.
PACKAGED = (HERE / "dcdisc").is_dir()
DCDISC = HERE if PACKAGED else ROOT / "third_party" / "dream-recomp" / "tools" / "dcdisc"
HASHES = HERE / "inputs.sha256" if PACKAGED else ROOT / "data" / "inputs.sha256"
sys.path.insert(0, os.environ.get("DCDISC_DIR", str(DCDISC)))


def expected_hash() -> str:
    for line in HASHES.read_text().splitlines():
        if line.endswith(f"  {BOOT_NAME}"):
            return line.split()[0]
    raise SystemExit(f"data/inputs.sha256 has no {BOOT_NAME}")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip())
        return 2
    from dcdisc.image import open_image
    from dcdisc.ipbin import parse_ipbin, read_ipbin
    from dcdisc.iso9660 import Iso9660

    gdi, out = sys.argv[1], pathlib.Path(sys.argv[2])
    with open_image(gdi) as image:
        boot_name = parse_ipbin(read_ipbin(image)).boot_filename
        data = Iso9660(image).read_path(boot_name)
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_hash():
        print(f"{boot_name} is SHA-256 {digest}, not what data/inputs.sha256 expects. This is a "
              "different release: stop, and tell the maintainer.", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"wrote {out}: {boot_name}, {len(data):,} bytes, SHA-256 matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
