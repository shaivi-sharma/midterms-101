"""Results and statements on disk.

results.json   the race data the page draws (edit it, or replace it with a feed, then rebuild)
examples.json  seven fictional statements with hand labels, used until real ones are verified
statements.json  the labeler's working set: real statements, Claude's labels, a person's labels
"""

import csv
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results.json"
EXAMPLES = HERE / "examples.json"
STATEMENTS = HERE / "statements.json"

FIELDS = ["text", "speaker", "kind", "race", "date", "url"]


def load_results() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def load_examples() -> list[dict]:
    return json.loads(EXAMPLES.read_text(encoding="utf-8"))


def load_statements() -> list[dict]:
    if not STATEMENTS.exists():
        return []
    return json.loads(STATEMENTS.read_text(encoding="utf-8"))


def save_statements(rows: list[dict]) -> None:
    tmp = STATEMENTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATEMENTS)


def statement_id(text: str) -> str:
    return hashlib.sha1(" ".join(text.split()).lower().encode()).hexdigest()[:10]


def new_statement(**fields) -> dict:
    text = " ".join(str(fields.get("text", "")).split())
    return {
        "id": statement_id(text),
        **{f: str(fields.get(f, "") or "").strip() for f in FIELDS},
        "text": text,
        "fictional": False,
        "claude": None, "claude_runs": [], "why": "", "unstable": [], "rule_problems": [],
        "human": None, "verified": False,
    }


def parse_csv(data: bytes) -> list[dict]:
    """A CSV with a "text" column; speaker, kind, race, date and url are optional."""
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    cols = {c.lower().strip(): c for c in reader.fieldnames or []}
    if "text" not in cols:
        raise ValueError('The CSV needs a "text" column.')
    rows = []
    for r in reader:
        rec = {f: r.get(cols[f], "") for f in FIELDS if f in cols}
        if str(rec.get("text", "")).strip():
            rows.append(new_statement(**rec))
    return rows


def merge(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], int]:
    """Add new statements, skipping any already in the set (same text)."""
    seen = {r["id"] for r in existing}
    added = [r for r in incoming if r["id"] not in seen and not seen.add(r["id"])]
    return existing + added, len(added)


def for_page(rows: list[dict]) -> list[dict]:
    """What the page shows: verified real statements, or the fictional examples if there are none yet."""
    keep = ["id", "kind", "speaker", "race", "date", "url", "text", "fictional", "human", "claude", "why"]
    verified = [{k: r.get(k) for k in keep} for r in rows if r.get("verified") and r.get("human") and not r.get("fictional")]
    return verified or load_examples()
