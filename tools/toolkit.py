#!/usr/bin/env python3
"""Toolkit manager — clone/update the curated external repos listed in toolkit.repos.toml.

Repos are shallow-cloned into .toolkit/<category>/<name>/ (gitignored; never commit them).

Usage:
  python3 tools/toolkit.py list [category]          # list registered repos
  python3 tools/toolkit.py search <term>            # search name/use/tags
  python3 tools/toolkit.py clone <target>           # target = name | tag (e.g. core) | category | all
  python3 tools/toolkit.py update <target>          # fast-forward existing clones
  python3 tools/toolkit.py path <name>              # print local clone path
  python3 tools/toolkit.py open <name>              # print the GitHub URL

Examples:
  python3 tools/toolkit.py clone core               # the default starter set
  python3 tools/toolkit.py clone scraping           # whole category
  python3 tools/toolkit.py clone moviepy            # one repo
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "toolkit.repos.toml"
CLONE_DIR = ROOT / ".toolkit"


def load_repos() -> list[dict]:
    if not MANIFEST.exists():
        sys.exit(f"Manifest not found: {MANIFEST}")
    with open(MANIFEST, "rb") as f:
        data = tomllib.load(f)
    return data.get("repo", [])


def resolve(repos: list[dict], target: str) -> list[dict]:
    t = target.lower()
    if t == "all":
        return repos
    by_cat = [r for r in repos if r["category"] == t]
    if by_cat:
        return by_cat
    by_tag = [r for r in repos if t in r.get("tags", [])]
    if by_tag:
        return by_tag
    by_name = [r for r in repos if r["name"].lower() == t]
    if by_name:
        return by_name
    # substring fallback on names
    partial = [r for r in repos if t in r["name"].lower()]
    if partial:
        return partial
    sys.exit(
        f"No repo/tag/category matches '{target}'. Try `list` or `search`.\n"
        f"Categories: video, design, strategy, scraping. Tags: e.g. core, ai, browser, awesome."
    )


def dest(repo: dict) -> Path:
    return CLONE_DIR / repo["category"] / repo["name"]


def clone_one(repo: dict) -> tuple[str, bool, str]:
    d = dest(repo)
    if (d / ".git").exists():
        return repo["name"], True, "already cloned (use `update`)"
    d.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", "--single-branch", repo["url"], str(d)]
    try:
        import subprocess

        r = subprocess.run(cmd, capture_output=True, text=True)
        ok = r.returncode == 0
        return repo["name"], ok, (r.stderr.strip().splitlines() or [""])[-1]
    except Exception as e:  # noqa: BLE001
        return repo["name"], False, str(e)


def do_clone(repos: list[dict], jobs: int) -> None:
    if not repos:
        sys.exit("Nothing matched.")
    print(f"Cloning {len(repos)} repo(s) into {CLONE_DIR.relative_to(ROOT)}/ ...\n")
    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = {ex.submit(clone_one, r): r for r in repos}
        for fut in as_completed(futs):
            name, ok, msg = fut.result()
            mark = "✓" if ok else "✗"
            if not ok:
                failures += 1
            print(f"  {mark} {name:32s} {msg if not ok else ''}")
    print(f"\nDone. {len(repos) - failures}/{len(repos)} ready.")


def do_update(repos: list[dict], jobs: int) -> None:
    import subprocess

    existing = [r for r in repos if (dest(r) / ".git").exists()]
    if not existing:
        print("Nothing to update — clone first.")
        return
    print(f"Updating {len(existing)} repo(s) ...\n")
    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = {
            ex.submit(
                lambda r: (
                    r["name"],
                    subprocess.run(
                        ["git", "-C", str(dest(r)), "pull", "--ff-only", "--depth", "1"],
                        capture_output=True,
                        text=True,
                    ),
                ),
                r,
            ): r
            for r in existing
        }
        for fut in as_completed(futs):
            name, r = fut.result()
            ok = r.returncode == 0
            failures += 0 if ok else 1
            print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\nDone. {len(existing) - failures}/{len(existing)} updated.")


def do_list(repos: list[dict], category: str | None) -> None:
    if category:
        repos = [r for r in repos if r["category"] == category]
    cur = None
    for r in sorted(repos, key=lambda x: (x["category"], x["name"])):
        if r["category"] != cur:
            cur = r["category"]
            print(f"\n── {cur} " + "─" * (50 - len(cur)))
        star = "*" if "core" in r.get("tags", []) else " "
        print(f" {star} {r['name']:30s} {'/'.join(r['url'].split('/')[-2:]):45s} {r.get('use', '')[:70]}")
    print("\n(* = core starter set — `clone core`)")


def do_search(repos: list[dict], term: str) -> None:
    t = term.lower()
    hits = [
        r
        for r in repos
        if t in r["name"].lower()
        or t in r.get("use", "").lower()
        or any(t in tag for tag in r.get("tags", []))
    ]
    if not hits:
        print(f"No matches for '{term}'.")
        return
    do_list(hits, None)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list")
    l.add_argument("category", nargs="?", choices=["video", "design", "strategy", "scraping"])
    s = sub.add_parser("search")
    s.add_argument("term")
    c = sub.add_parser("clone")
    c.add_argument("target")
    c.add_argument("--jobs", type=int, default=4)
    u = sub.add_parser("update")
    u.add_argument("target", nargs="?", default="all")
    u.add_argument("--jobs", type=int, default=4)
    pa = sub.add_parser("path")
    pa.add_argument("name")
    o = sub.add_parser("open")
    o.add_argument("name")
    args = p.parse_args()

    repos = load_repos()
    if args.cmd == "list":
        do_list(repos, args.category)
    elif args.cmd == "search":
        do_search(repos, args.term)
    elif args.cmd == "clone":
        do_clone(resolve(repos, args.target), args.jobs)
    elif args.cmd == "update":
        do_update(resolve(repos, args.target), args.jobs)
    elif args.cmd == "path":
        r = resolve(repos, args.name)[0]
        print(dest(r))
    elif args.cmd == "open":
        print(resolve(repos, args.name)[0]["url"])


if __name__ == "__main__":
    main()
