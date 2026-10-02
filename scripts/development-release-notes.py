#!/usr/bin/env python3
"""Describe a published development revision relative to the latest stable release."""
import argparse
import json
import re
import subprocess
from urllib.parse import quote

REPO = "kapdon/rocknix-desktop"


def api(endpoint, paginate=False):
    command = ["gh", "api", f"repos/{REPO}/{endpoint}"]
    if paginate:
        command += ["--paginate", "--slurp"]
    return json.loads(subprocess.check_output(command, text=True))


def notes(revision, built_at):
    latest = api("releases/latest")
    tag = latest["tag_name"]
    comparison = f"{quote(tag, safe='')}...{revision}"
    pages = api(f"compare/{comparison}?per_page=100", paginate=True)
    commits = [commit for page in pages for commit in page["commits"]]
    # GitHub compare returns paginated commits in chronological order.
    if len(commits) != pages[0]["total_commits"]:
        raise RuntimeError("Incomplete development comparison")
    lines = [f"Commit: `{revision}`", f"Built: {built_at}", "",
             "Rolling dev pre-release. The installer selects the latest successful build.", "",
             f"## Changes since {tag}", "",
             "Compared with the latest stable release, not the previous development build.", ""]
    for commit in commits:
        subject = commit["commit"]["message"].splitlines()[0]
        subject = re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", subject)
        lines.append(f"- {subject} ([{commit['sha'][:7]}]({commit['html_url']}))")
    if not commits:
        lines.append("No commits ahead of the latest stable release.")
    lines += ["", f"[Full comparison](https://github.com/{REPO}/compare/{comparison})", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision")
    parser.add_argument("built_at")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("revision must be a full commit SHA")
    print(notes(args.revision, args.built_at), end="")
