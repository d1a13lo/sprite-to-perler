"""Check the guide: links, anchors, unused images, personal information, sample totals.
    python docs/tools/check_docs.py
"""
import csv
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
GUIDE = DOCS / "USER_GUIDE.md"
# Personal Windows paths and e-mail addresses (generic patterns, no names).
PERSONAL = re.compile(r"(C:\\Users\\|C:/Users/|\\AppData\\|[\w.+-]+@[\w-]+\.(com|net|org))", re.I)


def slug(heading):
    """GitHub's heading anchor rules."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def main():
    text = GUIDE.read_text(encoding="utf-8")
    problems = []
    headings = {slug(h) for h in re.findall(r"^#{1,6} (.+)$", text, re.M)}
    links = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
    used = set()
    for link in links:
        if link.startswith("#"):
            if link[1:] not in headings:
                problems.append(f"broken anchor {link}")
        elif not link.startswith("http"):
            target = (DOCS / link).resolve()
            if not target.exists():
                problems.append(f"missing file {link}")
            used.add(target)
    for image in (DOCS / "images").glob("*.png"):
        if image.resolve() not in used:
            problems.append(f"unused image images/{image.name}")
    for path in [GUIDE, *DOCS.glob("README*.md"), *(DOCS / "sample-output").rglob("*.csv")]:
        for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if PERSONAL.search(line):
                problems.append(f"personal information in {path.name}:{n}")
    charts = DOCS / "sample-output" / "pip_mushroom_bead_charts"
    for name, column in [("pip_mushroom_original_colors.csv", "Beads"), ("pip_mushroom_perler_supplies.csv", "Beads")]:
        with open(charts / name, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        total = int(rows[-1][column])
        if total != 886 or sum(int(r[column]) for r in rows[:-1]) != total:
            problems.append(f"{name}: totals do not reconcile to 886")
    with open(charts / "pip_mushroom_board_counts.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if int(rows[-1]["Total beads"]) != 886:
        problems.append("board counts do not add up to 886")
    print(f"{len(links)} links checked, {len(headings)} headings, {len(used)} files referenced")
    print("\n".join(problems) if problems else "no problems found")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
