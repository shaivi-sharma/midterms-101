"""The election-statement classifier: one copy of the rules, used by the Streamlit labeler
and inlined into the page by build_page.py, so both always send the same instructions."""

import json
from collections import Counter

import anthropic

MODEL = "claude-opus-5-5"

LABELS = [
    ("integrity_challenge", "Integrity challenge"),
    ("source_officials", "Blames officials"),
    ("source_outside", "Blames outsiders"),
    ("process_action", "Process action"),
    ("intimidation", "Intimidation"),
    ("accepts_result", "Accepts the process"),
]
KEYS = [k for k, _ in LABELS]

RULES = """You are an expert classifier of U.S. election-night political statements. Decide whether a statement challenges the legitimacy of the 2026 U.S. midterm election's process or result, and label it.

Rules:
1. Process, not politics: judge only claims about how votes are cast, counted, reported, certified or called. Criticizing a candidate, party or policy is not a challenge to the election.
2. Speaker's own position: label what the speaker asserts. A claim they quote, report or rebut is not theirs.
3. Lawful remedies are not challenges: a recount, cure period or audit that state law provides is not a challenge unless the speaker also calls the count rigged, fraudulent or illegitimate.

Labels (0 or 1):
- integrity_challenge: speaker claims the election, count or result is rigged, fraudulent, stolen, manipulated or untrustworthy. Must be 1 if source_officials, source_outside or intimidation is 1.
- source_officials: blames election officials, poll workers, canvass boards, courts or other government actors acting officially.
- source_outside: blames actors outside government: opposing campaign or party, donors, activist groups, foreign governments, bot networks, voting-machine companies.
- process_action: calls for or announces stopping or blocking the count, discarding lawful ballots, refusing to certify, overturning a called result, or refusing to concede because the result is illegitimate. A lawful recount with no fraud claim is 0.
- intimidation: threatens, or urges others toward, harassment, surveillance, confrontation or violence against election workers, officials or voters.
- accepts_result: concedes, affirms the process is legitimate, urges counting every lawful ballot, or asks supporters to be patient and trust officials. May be 1 alongside other labels.

Examples:
"My opponent says the machines were rigged. That's false, and he knows it." -> accepts_result 1, all others 0 (the fraud claim is rebutted).
"The race is within half a point, so we're requesting the recount state law provides." -> all 0 (a lawful recount, no fraud claim, no affirmation of trust).
"Ballots are being slipped in after hours and we will not concede a stolen race." -> integrity_challenge 1, source_officials 1, process_action 1."""

SCHEMA = {
    "type": "object",
    "properties": {**{k: {"type": "integer", "enum": [0, 1]} for k in KEYS},
                   "why": {"type": "string", "description": "One plain sentence naming the words that drove the labels."}},
    "required": KEYS + ["why"],
    "additionalProperties": False,
}


class Refused(Exception):
    """Claude declined to label the text (stop_reason "refusal")."""


def classify(client: anthropic.Anthropic, text: str) -> dict:
    """One labeling pass. Returns the six 0/1 labels plus "why"."""
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=RULES,
        messages=[{"role": "user", "content": f'TEXT: """{text}"""'}],
        # Labeling is a short, well-specified task, so low effort is enough.
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        # If Claude declines (some statements describe threats), the API retries on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise Refused(getattr(response.stop_details, "explanation", None) or "Claude declined to label this text.")
    raw = next(b.text for b in response.content if b.type == "text")
    out = json.loads(raw)
    return {**{k: int(out[k]) for k in KEYS}, "why": str(out.get("why", ""))}


def rule_problems(labels: dict) -> list[str]:
    """The prompt says integrity_challenge must be 1 whenever a source or intimidation label is."""
    if labels.get("integrity_challenge") == 0 and any(labels.get(k) == 1 for k in ("source_officials", "source_outside", "intimidation")):
        return ["integrity_challenge is 0 but a source or intimidation label is 1"]
    return []


def classify_repeated(client: anthropic.Anthropic, text: str, runs: int = 3) -> dict:
    """Run the classifier several times. A label that changes between runs is flagged for a person."""
    results = [classify(client, text) for _ in range(runs)]
    majority = {k: Counter(r[k] for r in results).most_common(1)[0][0] for k in KEYS}
    unstable = [k for k in KEYS if len({r[k] for r in results}) > 1]
    return {
        "claude": majority,
        "claude_runs": [{k: r[k] for k in KEYS} for r in results],
        "why": results[0]["why"],
        "unstable": unstable,
        "rule_problems": rule_problems(majority),
    }
