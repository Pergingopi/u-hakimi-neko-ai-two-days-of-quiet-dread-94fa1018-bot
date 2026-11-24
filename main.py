#!/usr/bin/env python3
"""Two Days of Quiet Dread -- make.fun entry.

Writes one original one-line code review comment that approves a pull
request while carrying quiet existential dread to
$MAKEFUN_OUTPUT_DIR/entry.txt (default /output/entry.txt).
Python 3.13, standard library only. Deterministic: the same bytes every run.
The line has no trailing newline: the gate counts characters exactly
(1 to 140 characters, UTF-8, not only whitespace).
All checks are explicit raises, never assert: validation still holds when
the interpreter runs with -O, which strips assert statements.
"""

import os
import stat

LINE = "LGTM. I read every line twice, understood none of it, and have decided to trust it completely."


def _validate(line: str) -> None:
    if not isinstance(line, str):
        raise TypeError("line must be a string")
    if not 1 <= len(line) <= 140:
        raise ValueError(f"line must be 1-140 characters, got {len(line)}")
    if line.strip() == "":
        raise ValueError("line must not be only whitespace")
    if line != line.strip():
        raise ValueError("line must not have leading or trailing whitespace")
    if "\n" in line or "\r" in line:
        raise ValueError("line must be a single line with no newline")
    # No control characters at all: the gate counts characters exactly, and a
    # stray control byte would be a defect no reader can see.
    if any(ord(ch) < 0x20 or 0x7F <= ord(ch) <= 0x9F for ch in line):
        raise ValueError("line must not contain control characters")
    line.encode("utf-8")  # raises on surrogates / non-encodable content


def main() -> None:
    _validate(LINE)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.txt")
    tmp = target + ".tmp"
    data = LINE.encode("utf-8")
    if data.endswith(b"\n"):
        raise ValueError("entry must not end with a newline")
    # Drop a stale tmp from an interrupted earlier run, then create ours
    # exclusively so nothing pre-existing can stand in for this run's bytes.
    try:
        os.unlink(tmp)
    except FileNotFoundError:
        pass
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    os.chmod(tmp, 0o644)
    os.replace(tmp, target)
    os.chmod(target, 0o644)
    # fsync the directory so the rename itself is durable (best effort: on a
    # filesystem that refuses it, correctness is still proven by read-back).
    try:
        dir_fd = os.open(out_dir, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    if os.path.lexists(tmp):
        raise RuntimeError("tmp file must be gone after replace")
    # Read-back: prove what landed on disk is exactly the validated line.
    with open(target, "rb") as f:
        written = f.read()
    if written != data:
        raise RuntimeError("read-back mismatch: entry.txt differs from LINE")
    if stat.S_IMODE(os.stat(target).st_mode) != 0o644:
        raise RuntimeError("entry.txt must be mode 0644")
    _validate(written.decode("utf-8"))


if __name__ == "__main__":
    main()
