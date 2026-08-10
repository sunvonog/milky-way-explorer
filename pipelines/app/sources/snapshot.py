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
import urllib
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

CURRENT = "current"  # fixed subdirectory path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_dir(raw_root: Path, source: str) -> Path:
    """The single current-snapshot directory for a source."""
    return raw_root / source / CURRENT


def _promote_current(staged: Path, destination: Path):
    """Replace the current directory while retaining rollback on failure."""
    previous: Path | None = None

    try:
        if destination.exists():
            previous = destination.with_name(f".{CURRENT}.old-{staged.name}")
            destination.rename(previous)

        staged.rename(destination)
    except BaseException:
        if previous is not None and previous.exists():
            if destination.exists():
                shutil.rmtree(destination, ignore_errors=True)
            previous.rename(destination)
        raise
    else:
        if previous is not None:
            shutil.rmtree(previous, ignore_errors=True)


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
        _promote_current(tmp, dest)

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

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        detail = body[:2000] if body else str(exc.reason)

        raise RuntimeError(f"{source}: upstream returned HTTP {exc.code}.\n{detail}") from exc

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


def snapshot_directory(
    source_dir: Path,
    source: str,
    raw_root: Path,
    *,
    origin: str,
    fetched_online: bool,
) -> Path:
    """Publish a staged directory as one failure-safe current snapshot."""
    if not source_dir.is_dir():
        raise NotADirectoryError(f"snapshot source directory not found: {source_dir}")

    source_files = sorted(
        (path for path in source_dir.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(source_dir).as_posix(),
    )

    if not source_files:
        raise ValueError("snapshot directory must contain at least one file")

    relative_paths = [path.relative_to(source_dir) for path in source_files]

    if Path("snapshot.json") in relative_paths:
        raise ValueError("snapshot.json is reserved for snapshot metadata")

    destination = snapshot_dir(raw_root, source)
    destination.parent.mkdir(parents=True, exist_ok=True)

    staged = Path(tempfile.mkdtemp(dir=destination.parent, prefix=f".{CURRENT}.tmp-"))

    try:
        for source_path, relative_path in zip(source_files, relative_paths, strict=True):
            target = staged / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)

        files: list[dict[str, object]] = []
        total_bytes = 0
        tree_digest = hashlib.sha256()

        for relative_path in relative_paths:
            path = staged / relative_path
            payload = path.read_bytes()
            relative_name = relative_path.as_posix()

            files.append({"path": relative_name, "sha256": _sha256(payload), "bytes": len(payload)})

            total_bytes += len(payload)
            tree_digest.update(relative_name.encode("utf-8"))
            tree_digest.update(b"\0")
            tree_digest.update(payload)
            tree_digest.update(b"\0")

        metadata = {
            "source": source,
            "origin": origin,
            "fetched_at": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            "fetched_online": fetched_online,
            "sha256": tree_digest.hexdigest(),
            "bytes": total_bytes,
            "files": files,
        }

        (staged / "snapshot.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )

        _promote_current(staged, destination)
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise

    return destination
