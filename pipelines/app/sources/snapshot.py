"""Source snapshots, one current snapshot per source, versioned by git.

Design
------
Each source has a single fixed directory:
    data/raw/<source>/current/
        <original_filename>     the source bytes
        snapshot.json           checksum + origin metadata

Refreshing a source overwrites that directory. There are no timestamps in the
path: git history is the version history. To see how a source changed over time,
use ``git log data/raw/<source>/``; to reproduce a past build, check out that commit.
This keeps the working tree small while remaining fully reproducible.

Two entry points, one shared write path so both produce identical structure:
    * ``snapshot_local`` - copy a file you already have on disk (manual export, or a
        source that only offers a rendered page).
    * ``snapshot_url`` - download once (maintainer refresh path).

The write is atomic: bytes go to a temp dir which is swapped into place with a single
rename, so an interrupted refresh never leaves a half written snapshot that a build
might read.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

CURRENT = "current"  # fixed subdirectory path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_dir(raw_root: Path, source: str) -> Path:
    """The single current-snapshot directory for a source."""
    return raw_root / source / CURRENT


def _write_current(
    payload: bytes, filename: str, source: str, raw_root: Path, *, origin: str, fetched_online: bool
) -> Path:
    """Atomically replace the current snapshot for ``source``.

    Writes into a sibling temp dir, then swapsit into place with os.replace via
    shutil, so readers see either the old snapshot or the new one, never a
    partially-written mix.
    """
    dest = snapshot_dir(raw_root, source)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # stage in a temp dir next to the destination (same filesystem -> atomic swap)
    tmp = Path(tempfile.mkdtemp(dir=dest.parent, prefix=f".{CURRENT}.tmp-"))
    try:
        (tmp / filename).write_bytes(payload)
        meta = {
            "source": source,
            "origin": origin,
            "original_filename": filename,
            "fetched_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            "fetched_online": fetched_online,
            "sha256": _sha256(payload),
            "bytes": len(payload),
        }
        (tmp / "snapshot.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        # atomic replace of the whole directory
        if dest.exists():
            old = dest.with_name(f".{CURRENT}.old-{tmp.name}")
            dest.rename(old)
            tmp.rename(dest)
            shutil.rmtree(old)
        else:
            tmp.rename(dest)

    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return dest / filename


def snapshot_local(
    source_file: Path, source: str, raw_root: Path, *, origin: str | None = None
) -> Path:
    """Snapshot a local file as the current version of ``source``."""
    if not source_file.is_file():
        raise FileNotFoundError(f"source file not found: {source_file}")
    payload = source_file.read_bytes()
    return _write_current(
        payload,
        source_file.name,
        source,
        raw_root,
        origin=origin or f"local:{source_file.name}",
        fetched_online=False,
    )


def snapshot_url(
    url: str,
    source: str,
    raw_root: Path,
    *,
    filename: str | None = None,
    timeout: float = 30.0,
    expected_sha256: str | None = None,
) -> Path:
    """Download ``url`` and snapshot it as the current version of ``source``.

    ``expected_sha256`` (optional, since the commited file is the real pin) fails
    the refresh loudly if upstream bytes differ from what you expect - useful as a
    tripwire when refreshin.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "milky-way-explorer/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read()

    digest = _sha256(payload)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(
            f"{source}: upstream bytes differ from expected.\n"
            f"  expected    {expected_sha256}\n"
            f"  got         {digest}\n"
            f"Review the change, then update or drop the expected hash."
        )

    name = filename or Path(url).name or f"{source}.csv"
    return _write_current(payload, name, source, raw_root, origin=url, fetched_online=True)
