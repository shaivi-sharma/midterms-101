"""Build page/index.html: Midterms 101 with its data inlined.

Reads data/results.json, the verified statements from data/statements.json (or the fictional
examples), and the classifier rules from classifier.py, and writes them into page/template.html.
The output is one self-contained file with no server, the same file that's published as the artifact.

Note: the prose in Parts 1 and 3 (for example "Democrats take it", the stat cards, the dates to watch)
is written by hand in the template. Charts, the map, tables and lists follow the data; the prose doesn't.
"""

import json
from pathlib import Path

from classifier import RULES
from data import store

PAGE = Path(__file__).parent / "page"


def render() -> str:
    payload = {
        "results": store.load_results(),
        "statements": store.for_page(store.load_statements()),
        "rules": RULES,
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    template = (PAGE / "template.html").read_text(encoding="utf-8")
    assert "/*DATA*/" in template, "page/template.html is missing its /*DATA*/ slot"
    return template.replace("/*DATA*/", data.replace("</", "<\\/"), 1)


def check(results: dict) -> list[str]:
    """Totals that should always hold, so a bad edit to results.json is caught before publishing."""
    problems = []
    s = results["senate"]
    won = {p: sum(1 for r in s if r["status"] == p) for p in ("D", "R", "I")}
    total = results["senate_holdovers"]["D"] + results["senate_holdovers"]["R"] + len(s)
    if total != 100:
        problems.append(f"Senate seats add to {total}, not 100.")
    h = results["house"]
    if h["D"] + h["R"] + h["uncalled"] != 435:
        problems.append(f"House seats add to {h['D'] + h['R'] + h['uncalled']}, not 435.")
    if len(h["open"]) != h["uncalled"]:
        problems.append(f"House lists {len(h['open'])} uncalled districts but says {h['uncalled']}.")
    open_senate = sum(1 for r in s if r["status"] == "open")
    print(f"Senate: {results['senate_holdovers']['D'] + won['D']} D, {results['senate_holdovers']['R'] + won['R']} R, "
          f"{won['I']} I, {open_senate} uncalled")
    return problems


if __name__ == "__main__":
    for p in check(store.load_results()):
        print("WARNING:", p)
    html = render()
    (PAGE / "index.html").write_text(html, encoding="utf-8")
    shown = store.for_page(store.load_statements())
    kind = "fictional examples" if shown and shown[0].get("fictional") else "verified statements"
    print(f"page/index.html {len(html):,} bytes · {len(shown)} {kind}")
