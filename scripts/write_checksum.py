"""
scripts/write_checksum.py
=========================
Writes a download's fingerprint file for a release:

    python scripts/write_checksum.py LockIn-Windows.zip

makes LockIn-Windows.zip.sha256, holding "<fingerprint>  LockIn-Windows.zip"
(the same layout the `sha256sum` tool uses). The app reads this file and
only installs an update whose download matches it -- see
lock_in/update_verify.py. The release build (.github/workflows/release.yml)
runs this for every download.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lock_in.update_verify import checksum_asset_name, parse_checksum, sha256_of


def write_checksum(archive: Path) -> Path:
    digest = sha256_of(archive)
    out = archive.with_name(checksum_asset_name(archive.name))
    out.write_text(f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")
    # Read it straight back with the app's own reader, so a file the app
    # couldn't read can never be published.
    if parse_checksum(out.read_text(encoding="utf-8"), archive.name) != digest:
        raise SystemExit(f"The fingerprint file for {archive.name} didn't read back correctly")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/write_checksum.py <download file>")
    print(write_checksum(Path(sys.argv[1])))
