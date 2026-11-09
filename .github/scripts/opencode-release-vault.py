#!/usr/bin/env python3
"""Stream encrypted project snapshots to GitHub Release assets, not Git history.

Every asset is AES-256-GCM authenticated by opencode-crypto.mjs.
A release is published ONLY after every asset and its encrypted manifest uploads.
No provider token, private path, or project file is uploaded unencrypted.
"""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ["GITHUB_WORKSPACE"])
TEMP = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
CRYPTO = HERE / "opencode-crypto.mjs"
TEST_BACKEND = os.environ.get("VAULT_TEST_DIR")
PREFIX = "ocvault-"
CHUNK_MIB = int(os.environ.get("VAULT_CHUNK_MIB", "256"))
if CHUNK_MIB < 1 or CHUNK_MIB > 1536:
    raise ValueError("VAULT_CHUNK_MIB must be between 1 and 1536")
CHUNK_LIMIT = CHUNK_MIB * 1024 * 1024
MAX_PARTS = 999
spec = importlib.util.spec_from_file_location("project_helper", HERE / "opencode-project-files.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

def cmd(*args):
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout

def crypt(action, source, destination):
    cmd("node", str(CRYPTO), action, str(source), str(destination))

class Storage:
    def __init__(self):
        self.local = Path(TEST_BACKEND) if TEST_BACKEND else None
        self.repository = os.environ.get("GH_REPO", os.environ.get("GITHUB_REPOSITORY", ""))
        if not self.local and not self.repository:
            raise RuntimeError("GH_REPO or GITHUB_REPOSITORY must be set")
        if self.local:
            self.local.mkdir(parents=True, exist_ok=True)

    def create(self, tag):
        if self.local:
            (self.local / tag).mkdir()
        else:
            cmd("gh", "release", "create", tag, "-R", self.repository, "--target", "main",
                "--draft", "--latest=false", "--title", "Encrypted OpenCode project snapshot",
                "--notes", "Encrypted developer workspace checkpoint. No plaintext assets.")

    def upload(self, tag, path):
        if self.local:
            shutil.copy2(path, self.local / tag / path.name)
        else:
            cmd("gh", "release", "upload", tag, str(path), "-R", self.repository)

    def publish(self, tag):
        if self.local:
            (self.local / tag / "PUBLISHED").touch()
        else:
            cmd("gh", "release", "edit", tag, "-R", self.repository, "--draft=false", "--latest=false")

    def list(self):
        if self.local:
            names = [p.name for p in self.local.iterdir() if p.is_dir()
                     and p.name.startswith(PREFIX) and (p / "PUBLISHED").exists()]
        else:
            info = json.loads(cmd("gh", "release", "list", "-R", self.repository,
                                  "--limit", "100", "--json", "tagName,isDraft"))
            names = [r["tagName"] for r in info if not r["isDraft"]
                     and r["tagName"].startswith(PREFIX)]
        return sorted(names, reverse=True)

    def download(self, tag, filename, directory):
        if not re.fullmatch(r"(?:part-[0-9]{4}|manifest)\.enc", filename):
            raise ValueError("Invalid encrypted asset name")
        if self.local:
            shutil.copy2(self.local / tag / filename, directory / filename)
        else:
            cmd("gh", "release", "download", tag, "-R", self.repository,
                "--pattern", filename, "--dir", str(directory))
        if not (directory / filename).is_file():
            raise RuntimeError("Missing release asset: " + filename)

    def delete(self, tag):
        if self.local:
            shutil.rmtree(self.local / tag)
        else:
            cmd("gh", "release", "delete", tag, "-R", self.repository, "--yes", "--cleanup-tag")

# Never back up the runner's system, checkout .git internals, SSH credentials or temporary jobs.
SKIP = {".git", "node_modules", ".venv", "venv", ".next", "dist", "build",
        "target", "__pycache__", ".cache", ".npm", ".rustup", ".nvm", ".ssh",
        ".aws", ".azure", ".kube", ".gnupg", ".docker", "_tool", "_actions",
        "_temp", ".git-credentials", ".netrc"}
def include_member(member):
    parts = PurePosixPath(member.name).parts
    if len(parts) < 3:
        return member
    if any(item in SKIP for item in parts[2:]):
        return None
    root = parts[1]
    path_parts = parts[2:]
    if root == "home" and path_parts[0] == "work":
        return None
    if root == "home" and path_parts[:3] == (".local", "share", "opencode"):
        return None
    if root == "home" and path_parts[:2] == (".config", "opencode"):
        return None
    if root == "repository" and path_parts[0] in (".github", "cloud-workspace"):
        return None
    if root == "tmp" and (path_parts[0].startswith("opencode-")
                           or path_parts[0].startswith("systemd-private-")
                           or path_parts[0].startswith("snap-private-")):
        return None
    if member.issym() or member.islnk():
        return None  # Never follow or restore links outside snapshot roots.
    return member


def add_accessible(archive, source, arcname, skipped):
    """Archive accessible files; do not abort an entire release for protected /tmp entries.

    Resolve each child independently instead of tarfile.add(recursive=True),
    whose os.listdir() raises on snap-private-tmp and aborts the whole stream.
    Important unreadable paths are counted and reported; no data is silently claimed saved.
    """
    try:
        member = archive.gettarinfo(str(source), arcname=arcname)
    except (PermissionError, FileNotFoundError) as error:
        skipped.append((str(source), type(error).__name__))
        return
    if member is None:
        return
    member = include_member(member)
    if member is None:
        return
    if member.isdir():
        try:
            children = sorted(os.listdir(source))
        except (PermissionError, FileNotFoundError) as error:
            skipped.append((str(source), type(error).__name__))
            return
        archive.addfile(member)
        for child in children:
            add_accessible(archive, Path(source) / child,
                           str(PurePosixPath(arcname) / child), skipped)
    elif member.isfile():
        try:
            fileobj = open(source, "rb")
        except (PermissionError, FileNotFoundError) as error:
            skipped.append((str(source), type(error).__name__))
            return
        with fileobj:
            archive.addfile(member, fileobj)
    # Symlinks, device nodes and sockets are excluded from cross-runner backups.


class Sink:
    def __init__(self, store, tag, directory):
        self.store, self.tag, self.directory = store, tag, directory
        self.hash = hashlib.sha256()
        self.total = 0
        self.parts = []
        self.file = None
        self.current = 0

    def write(self, data):
        mv = memoryview(data)
        offset = 0
        while offset < len(mv):
            if self.file is None:
                self.file = open(self.directory / "part.tmp", "wb")
                self.current = 0
            n = min(CHUNK_LIMIT - self.current, len(mv) - offset)
            block = mv[offset:offset + n]
            self.file.write(block)
            self.hash.update(block)
            self.total += n
            self.current += n
            offset += n
            if self.current == CHUNK_LIMIT:
                self.flush_part()
        return len(data)

    def flush(self):
        if self.file:
            self.file.flush()

    def flush_part(self):
        if self.file is None:
            return
        self.file.close()
        self.file = None
        if len(self.parts) >= MAX_PARTS:
            raise RuntimeError("Exceeded 999 encrypted release parts")
        filename = f"part-{len(self.parts):04d}.enc"
        plain = self.directory / "part.tmp"
        encrypted = self.directory / filename
        crypt("encrypt", plain, encrypted)
        self.store.upload(self.tag, encrypted)
        self.parts.append(filename)
        plain.unlink()
        encrypted.unlink()
        self.current = 0

    def close(self):
        self.flush_part()

def roots():
    entries = helper.paths()
    # Older OpenCode builds can keep large undo/history snapshots outside SQLite.
    application_data = Path.home() / ".local" / "share" / "opencode"
    for subfolder in ("snapshot", "project", "storage", "tool-output"):
        candidate = application_data / subfolder
        if candidate.is_dir():
            entries["opencode-" + subfolder] = str(candidate)
    cloud = REPO / "cloud-workspace"
    if cloud.is_dir():
        entries["cloud"] = str(cloud)
    return {name: location for name, location in entries.items()
            if helper.safe_path(location) and Path(location).is_dir()}

def save():
    store = Storage()
    label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    tag = PREFIX + label + "-" + str(os.environ.get("GITHUB_RUN_ID", "local")) + "-" + secrets.token_hex(3)
    with tempfile.TemporaryDirectory(prefix="ocvault-", dir=TEMP) as directory:
        folder = Path(directory)
        sink = Sink(store, tag, folder)
        store.create(tag)
        try:
            entries = roots()
            skipped = []
            with tarfile.open(fileobj=sink, mode="w|gz", compresslevel=1) as archive:
                raw = json.dumps(entries, sort_keys=True).encode()
                info = tarfile.TarInfo("root-map.json")
                info.size = len(raw)
                info.mode = 0o600
                archive.addfile(info, io.BytesIO(raw))
                for name, location in sorted(entries.items()):
                    add_accessible(archive, location, "projects/" + name, skipped)
            sink.close()
            if skipped:
                print(f"::warning::OpenCode vault skipped {len(skipped)} inaccessible filesystem "
                      "item(s). Ensure important project folders have read permission.",
                      file=sys.stderr)
            manifest = {
                "version": 1, "parts": sink.parts,
                "compressed_sha256": sink.hash.hexdigest(), "compressed_bytes": sink.total
            }
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            crypt("encrypt", folder / "manifest.json", folder / "manifest.enc")
            store.upload(tag, folder / "manifest.enc")
            store.publish(tag)
        except Exception:
            print("Release snapshot did not publish; last valid checkpoint remains.", file=sys.stderr)
            raise
    # Keep 3 published project snapshots. Never delete other releases.
    for old in store.list()[3:]:
        try:
            store.delete(old)
        except Exception as error:
            print("Warning: unable to prune old snapshot:", type(error).__name__, file=sys.stderr)
    print(f"Encrypted project release published: {tag} ({sink.total} compressed bytes, {len(sink.parts)} parts)")

class Reader:
    def __init__(self, store, tag, manifest, folder):
        self.store, self.tag, self.manifest, self.folder = store, tag, manifest, folder
        self.parts = iter(manifest["parts"])
        self.fp = None
        self.active = None
        self.hash = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        if size < 0:
            size = 1024 * 1024
        out = bytearray()
        while len(out) < size:
            if self.fp is None:
                try:
                    item = next(self.parts)
                except StopIteration:
                    break
                if not re.fullmatch(r"part-[0-9]{4}\.enc", item):
                    raise ValueError("Unsafe release chunk name")
                self.store.download(self.tag, item, self.folder)
                plain = self.folder / "chunk.tmp"
                crypt("decrypt", self.folder / item, plain)
                (self.folder / item).unlink()
                self.fp = open(plain, "rb")
                self.active = plain
            chunk = self.fp.read(min(1024*1024, size - len(out)))
            if not chunk:
                self.fp.close()
                self.fp = None
                self.active.unlink()
                continue
            out.extend(chunk)
            self.hash.update(chunk)
            self.count += len(chunk)
        return bytes(out)

    def close(self):
        if self.fp:
            self.fp.close()
        if self.active and self.active.exists():
            self.active.unlink()

def restore():
    store = Storage()
    releases = store.list()
    if not releases:
        print("No large release snapshot yet; previous small Git checkpoint will still restore.")
        return
    tag = releases[0]
    with tempfile.TemporaryDirectory(prefix="ocvault-restore-", dir=TEMP) as directory:
        folder = Path(directory)
        store.download(tag, "manifest.enc", folder)
        crypt("decrypt", folder / "manifest.enc", folder / "manifest.json")
        manifest = json.loads((folder / "manifest.json").read_text())
        names = manifest.get("parts")
        if manifest.get("version") != 1 or not isinstance(names, list) or not 1 <= len(names) <= MAX_PARTS:
            raise ValueError("Invalid release snapshot manifest")
        if len(names) != len(set(names)) or any(not re.fullmatch(r"part-[0-9]{4}\.enc", x) for x in names):
            raise ValueError("Unsafe release asset list")
        expected = manifest.get("compressed_sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid archive digest")
        reader = Reader(store, tag, manifest, folder)
        root_map = None
        try:
            with tarfile.open(fileobj=reader, mode="r|gz") as archive:
                for item in archive:
                    if item.name == "root-map.json" and item.isfile():
                        root_map = json.loads(archive.extractfile(item).read())
                        if not isinstance(root_map, dict) or len(root_map) > 1000:
                            raise ValueError("Invalid project root map")
                        continue
                    path = PurePosixPath(item.name).parts
                    if len(path) < 2 or path[0] != "projects" or root_map is None:
                        continue
                    name = path[1]
                    if name not in root_map or len(path) < 3 or ".." in path:
                        continue
                    location = root_map[name]
                    if not isinstance(location, str):
                        raise ValueError("Unsafe project location")
                    base = helper.safe_path(location)
                    if base is None:
                        raise ValueError("Unsafe restore root")
                    output = base.joinpath(*path[2:])
                    if not output.resolve(strict=False).is_relative_to(base.resolve(strict=False)):
                        raise ValueError("Unsafe archive member")
                    if item.isdir():
                        output.mkdir(parents=True, exist_ok=True)
                    elif item.isfile():
                        output.parent.mkdir(parents=True, exist_ok=True)
                        stream = archive.extractfile(item)
                        with open(output, "wb") as target:
                            shutil.copyfileobj(stream, target, length=1024*1024)
                        output.chmod(item.mode & 0o777)
            # Tar readers can stop at a trailing zero block. Consume remaining gzip bytes for checksum.
            while reader.read(1024*1024):
                pass
            if reader.hash.hexdigest() != expected or reader.count != manifest.get("compressed_bytes"):
                raise ValueError("Compressed release checksum mismatch")
        finally:
            reader.close()
    print("Project folders restored from verified encrypted release:", tag)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("save", "restore"):
        raise SystemExit("Usage: opencode-release-vault.py save|restore")
    try:
        (save if sys.argv[1] == "save" else restore)()
    except Exception as error:
        print("OpenCode release vault error:", str(error), file=sys.stderr)
        raise SystemExit(1)
