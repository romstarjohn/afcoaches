#!/usr/bin/env python3
"""Deterministic backlog document tooling.

Open backlog docs:   docs/backlogs/<6digits>-<slug>.md
Closed backlog docs: docs/backlogs/closed/<6digits>-<slug>.md
Template:            docs/backlogs/000000-template.md
Next id counter:     docs/backlogs/next-id

Standard library only. Run `tools/backlog.py --help` for commands.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import fcntl
import re
import sys
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
ID_WIDTH = 6
DOC_RE = re.compile(r"^(\d{6})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEMPLATE_ID = "000000"
CLOSE_TYPES = ("done", "stale", "duplicate", "superseded", "wontfix")
DUPLICATE_THRESHOLD = 0.5

STOPWORDS = {
    # en
    "a",
    "an",
    "and",
    "the",
    "of",
    "for",
    "to",
    "in",
    "on",
    "with",
    "by",
    "is",
    "be",
    "or",
    # fr
    "le",
    "la",
    "les",
    "un",
    "une",
    "des",
    "de",
    "du",
    "et",
    "pour",
    "dans",
    "sur",
    "avec",
    "au",
    "aux",
    # de
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "und",
    "fur",
    "mit",
    "von",
    "zu",
    "im",
    "auf",
}


class BacklogError(Exception):
    """User-facing error; printed without traceback."""


# --------------------------------------------------------------------------- paths


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def open_dir(self) -> Path:
        return self.root / "docs" / "backlogs"

    @property
    def closed_dir(self) -> Path:
        return self.open_dir / "closed"

    @property
    def next_id_file(self) -> Path:
        return self.open_dir / "next-id"

    @property
    def lock_file(self) -> Path:
        return self.open_dir / ".next-id.lock"


def iter_docs(directory: Path):
    """Yield (id, slug, path) for backlog docs in a directory, excluding the template."""
    if not directory.is_dir():
        return
    for path in sorted(directory.iterdir()):
        m = DOC_RE.match(path.name)
        if path.is_file() and m and m.group(1) != TEMPLATE_ID:
            yield m.group(1), m.group(2), path


def max_existing_id(paths: Paths) -> int:
    ids = [int(i) for d in (paths.open_dir, paths.closed_dir) for i, _, _ in iter_docs(d)]
    return max(ids, default=0)


def fmt_id(n: int) -> str:
    if not 0 < n < 10**ID_WIDTH:
        raise BacklogError(f"id out of range: {n}")
    return f"{n:0{ID_WIDTH}d}"


# --------------------------------------------------------------------------- id allocation


@contextmanager
def locked(paths: Paths):
    paths.open_dir.mkdir(parents=True, exist_ok=True)
    with open(paths.lock_file, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def read_next_id(paths: Paths) -> int:
    if not paths.next_id_file.exists():
        raise BacklogError(
            f"{paths.next_id_file.relative_to(paths.root)} missing; run `tools/backlog.py init-next-id` first"
        )
    raw = paths.next_id_file.read_text().strip()
    if not raw.isdigit():
        raise BacklogError(f"invalid next-id content: {raw!r}")
    return int(raw)


def init_next_id(paths: Paths) -> int:
    with locked(paths):
        if paths.next_id_file.exists():
            return read_next_id(paths)
        value = max_existing_id(paths) + 1
        paths.next_id_file.write_text(f"{value}\n")
        return value


def alloc_id(paths: Paths) -> str:
    with locked(paths):
        value = read_next_id(paths)
        # Never hand out an id that already exists on disk (e.g. after manual edits).
        value = max(value, max_existing_id(paths) + 1)
        paths.next_id_file.write_text(f"{value + 1}\n")
        return fmt_id(value)


# --------------------------------------------------------------------------- duplicates


def normalize_tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return {t for t in re.split(r"[^a-z0-9]+", text) if t and t not in STOPWORDS}


def read_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].removeprefix("Backlog:").strip()
    return ""


def similarity(title: str, slug: str, other_title: str, other_slug: str) -> float:
    if slug == other_slug:
        return 1.0
    a = normalize_tokens(title) | normalize_tokens(slug)
    b = normalize_tokens(other_title) | normalize_tokens(other_slug)
    jaccard = len(a & b) / len(a | b) if a | b else 0.0
    seq = difflib.SequenceMatcher(None, slug, other_slug).ratio()
    return round(max(jaccard, seq * 0.9), 3)


def find_duplicates(paths: Paths, title: str, slug: str, threshold: float = DUPLICATE_THRESHOLD):
    """Return [(score, path)] for OPEN docs similar to the given title/slug, best first."""
    hits = []
    for _, other_slug, path in iter_docs(paths.open_dir):
        score = similarity(title, slug, read_title(path), other_slug)
        if score >= threshold:
            hits.append((score, path))
    return sorted(hits, key=lambda h: (-h[0], h[1].name))


# --------------------------------------------------------------------------- create


DEFERRED_FIELDS = ("deferred_from", "defer_reason", "findings", "direction_hint")


def render_doc(doc_id: str, today: str, f: dict[str, str | None]) -> str:
    def section(heading: str, body: str | None) -> str:
        return f"## {heading}\n\n{(body or '').strip() or '_None._'}\n"

    parts = [
        f"# Backlog: {f['title']}\n",
        f"- **ID:** {doc_id}\n- **Slug:** {f['slug']}\n- **Status:** open\n- **Created:** {today}\n",
        section("Summary", f["summary"]),
        section("Reference", f["reference"]),
        section("Scope Hint", f["scope_hint"]),
        section("Acceptance Hint", f["acceptance_hint"]),
    ]
    if any(f.get(k) for k in DEFERRED_FIELDS):
        parts += [
            "## Deferral Context\n",
            "### Deferred From\n\n" + f["deferred_from"].strip() + "\n",
            "### Defer Reason\n\n" + f["defer_reason"].strip() + "\n",
            "### Findings\n\n" + f["findings"].strip() + "\n",
            "### Direction Hint\n\n" + f["direction_hint"].strip() + "\n",
        ]
    if f.get("notes"):
        parts.append(section("Notes", f["notes"]))
    return "\n".join(parts)


def create_doc(paths: Paths, fields: dict[str, str | None], doc_id: str | None, today: str | None = None) -> Path:
    slug = fields["slug"] or ""
    if not SLUG_RE.match(slug):
        raise BacklogError(f"invalid slug {slug!r}: use lowercase a-z, 0-9 and single hyphens")
    for key in ("title", "summary", "reference", "scope_hint", "acceptance_hint"):
        if not (fields.get(key) or "").strip():
            raise BacklogError(f"missing required field: {key.replace('_', '-')}")
    given = [k for k in DEFERRED_FIELDS if (fields.get(k) or "").strip()]
    if given and len(given) != len(DEFERRED_FIELDS):
        missing = [k.replace("_", "-") for k in DEFERRED_FIELDS if k not in given]
        raise BacklogError(f"deferred-work context is all-or-nothing; missing: {', '.join(missing)}")

    if doc_id is None:
        doc_id = alloc_id(paths)
    elif not re.fullmatch(r"\d{6}", doc_id) or doc_id == TEMPLATE_ID:
        raise BacklogError(f"invalid id {doc_id!r}: expected 6 digits, not {TEMPLATE_ID}")

    for _, _, existing in [*iter_docs(paths.open_dir), *iter_docs(paths.closed_dir)]:
        if existing.name.startswith(doc_id + "-"):
            raise BacklogError(f"id {doc_id} already used by {existing.relative_to(paths.root)}")

    paths.open_dir.mkdir(parents=True, exist_ok=True)
    target = paths.open_dir / f"{doc_id}-{slug}.md"
    content = render_doc(doc_id, today or dt.date.today().isoformat(), fields)
    with open(target, "x", encoding="utf-8") as fh:  # "x" refuses to overwrite
        fh.write(content)
    return target


# --------------------------------------------------------------------------- close / search


def search_by_id(paths: Paths, doc_id: str, scope: str) -> list[Path]:
    dirs = {"open": [paths.open_dir], "closed": [paths.closed_dir], "all": [paths.open_dir, paths.closed_dir]}[scope]
    return [p for d in dirs for i, _, p in iter_docs(d) if i == doc_id]


def resolve_open_doc(paths: Paths, path: str | None, doc_id: str | None) -> Path:
    if path:
        p = Path(path)
        p = (p if p.is_absolute() else paths.root / p).resolve()
        if p.parent != paths.open_dir.resolve() or not DOC_RE.match(p.name) or p.name.startswith(TEMPLATE_ID):
            raise BacklogError(f"not an open backlog doc: {path}")
        if not p.is_file():
            raise BacklogError(f"file not found: {path}")
        return p
    matches = search_by_id(paths, doc_id or "", "open")
    if len(matches) != 1:
        raise BacklogError(f"expected exactly one open backlog doc with id {doc_id}, found {len(matches)}")
    return matches[0]


def close_doc(
    paths: Paths, target: Path, close_type: str, detail: str, reference: str | None, today: str | None = None
) -> Path:
    if close_type not in CLOSE_TYPES:
        raise BacklogError(f"invalid close type {close_type!r}; choose one of {', '.join(CLOSE_TYPES)}")
    if not detail.strip():
        raise BacklogError("close detail must not be empty")
    today = today or dt.date.today().isoformat()
    text = target.read_text(encoding="utf-8")
    if "\n## Close Reason" in text:
        raise BacklogError(f"{target.name} already has a Close Reason section")
    text, n = re.subn(
        r"^- \*\*Status:\*\* open$", f"- **Status:** closed\n- **Closed:** {today}", text, count=1, flags=re.M
    )
    if n != 1:
        raise BacklogError(f"{target.name}: could not find '- **Status:** open' line")
    text = text.rstrip("\n") + f"\n\n## Close Reason\n\n- **Type:** {close_type}\n\n{detail.strip()}\n"
    if reference and reference.strip():
        text += f"\n### Close Reference\n\n{reference.strip()}\n"

    paths.closed_dir.mkdir(parents=True, exist_ok=True)
    dest = paths.closed_dir / target.name
    if dest.exists():
        raise BacklogError(f"{dest.relative_to(paths.root)} already exists")
    dest.write_text(text, encoding="utf-8")
    target.unlink()
    return dest


# --------------------------------------------------------------------------- CLI


def text_arg(parser: argparse.ArgumentParser, name: str, help_text: str) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(f"--{name}", help=help_text)
    group.add_argument(f"--{name}-file", help=f"read {name} from file (use for multiline/markdown text)")


def get_text(args: argparse.Namespace, name: str) -> str | None:
    attr = name.replace("-", "_")
    file_value = getattr(args, attr + "_file", None)
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return getattr(args, attr, None)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="backlog.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-next-id", help="create docs/backlogs/next-id from existing docs")
    sub.add_parser("alloc-id", help="allocate and print the next id")

    fd = sub.add_parser("find-duplicates", help="list similar OPEN backlog docs")
    fd.add_argument("--title", required=True)
    fd.add_argument("--slug", required=True)
    fd.add_argument("--threshold", type=float, default=DUPLICATE_THRESHOLD)

    cd = sub.add_parser("create-doc", help="create a new open backlog doc")
    cd.add_argument("--title", required=True)
    cd.add_argument("--slug", required=True)
    for name, h in [
        ("summary", "what and why"),
        ("reference", "evidence/discussion"),
        ("scope-hint", "expected scope"),
        ("acceptance-hint", "done criteria"),
        ("notes", "optional notes"),
        ("deferred-from", "source task/RFC"),
        ("defer-reason", "why postponed"),
        ("findings", "what was learned"),
        ("direction-hint", "what future planning should revisit/prefer/avoid"),
    ]:
        text_arg(cd, name, h)
    ids = cd.add_mutually_exclusive_group(required=True)
    ids.add_argument("--auto-id", action="store_true", help="allocate id from next-id")
    ids.add_argument("--id", help="explicit 6-digit id")

    cl = sub.add_parser("close-doc", help="close an open backlog doc and move it to closed/")
    target = cl.add_mutually_exclusive_group(required=True)
    target.add_argument("--path")
    target.add_argument("--id")
    cl.add_argument("--type", required=True, choices=CLOSE_TYPES)
    text_arg(cl, "detail", "close reason detail (required)")
    text_arg(cl, "reference", "optional supporting reference")

    sb = sub.add_parser("search-by-id", help="resolve a backlog id to its path")
    sb.add_argument("--id", required=True)
    sb.add_argument("--scope", choices=("open", "closed", "all"), default="open")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = Paths(args.root.resolve())
    rel = lambda p: p.relative_to(paths.root).as_posix()  # noqa: E731
    try:
        if args.cmd == "init-next-id":
            print(f"next-id: {init_next_id(paths)}")
        elif args.cmd == "alloc-id":
            print(alloc_id(paths))
        elif args.cmd == "find-duplicates":
            hits = find_duplicates(paths, args.title, args.slug, args.threshold)
            if not hits:
                print("No duplicate candidates.")
            for score, path in hits:
                print(f"{score:.2f}\t{rel(path)}\t{read_title(path)}")
        elif args.cmd == "create-doc":
            fields = {"title": args.title, "slug": args.slug}
            for name in (
                "summary",
                "reference",
                "scope-hint",
                "acceptance-hint",
                "notes",
                "deferred-from",
                "defer-reason",
                "findings",
                "direction-hint",
            ):
                fields[name.replace("-", "_")] = get_text(args, name)
            print(rel(create_doc(paths, fields, None if args.auto_id else args.id)))
        elif args.cmd == "close-doc":
            detail = get_text(args, "detail")
            if not detail:
                raise BacklogError("--detail or --detail-file is required")
            target = resolve_open_doc(paths, args.path, args.id)
            print(rel(close_doc(paths, target, args.type, detail, get_text(args, "reference"))))
        elif args.cmd == "search-by-id":
            matches = search_by_id(paths, args.id, args.scope)
            if not matches:
                print(f"No backlog doc with id {args.id} in scope {args.scope}.", file=sys.stderr)
                return 1
            for m in matches:
                print(rel(m))
    except (BacklogError, FileNotFoundError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
