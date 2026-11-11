"""Midterms 101 workbench: the results, a statement labeler, and the button that rebuilds the page."""

import os

import anthropic
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import build_page
import classifier
from data import store

st.set_page_config(page_title="Midterms 101 · Workbench", page_icon="🗳️", layout="wide",
                   initial_sidebar_state="collapsed")

# Tokens shared with page/template.html
C = {"bg": "#191817", "surface": "#211f1d", "ink": "#fffad7", "ink2": "#cfc9ac", "ink3": "#8f8a77", "rule": "#3a3733",
     "D": "#4d84ee", "R": "#e0533d", "I": "#9a4fc6", "now": "#ffb102", "ok": "#5fd3c9"}
T = {"D": "#9dbcff", "R": "#ff8a65", "I": "#d795ff"}
PARTY = {"D": "Democrat", "R": "Republican", "I": "Independent"}

st.markdown(f"""
<style>
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebar"] {{ display: none; }}
.block-container {{ max-width: 1120px; padding-top: 2.75rem; }}
h1, h2, h3 {{ font-weight: 400 !important; letter-spacing: 0 !important; }}
h3 {{ font-size: 1.45rem !important; margin-top: 1.2rem !important; }}
.eyebrow {{ font-family: 'DM Mono', monospace; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: {C['ink3']}; }}
.masthead h1 {{ font-size: clamp(36px, 6vw, 60px) !important; line-height: 1.02 !important; padding: 6px 0 10px !important; }}
.lede {{ font-family: 'Iowan Old Style', 'Source Serif 4', Georgia, serif; font-size: 20px; line-height: 1.5;
        color: {C['ink2']}; max-width: 62ch; margin: 0 0 8px; }}
.w-d {{ color: {T['D']}; }} .w-r {{ color: {T['R']}; }} .w-now {{ color: {C['now']}; }}
.cards {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px;
         padding: 16px 0 10px; border-block: 1px solid {C['rule']}; margin: 6px 0 14px; }}
.card .name {{ font-weight: 700; font-size: 14px; }}
.card .big {{ font-family: 'Young Serif', serif; font-size: clamp(24px, 3vw, 34px); line-height: 1.15; margin-top: 4px; }}
.card .sub {{ font-family: 'DM Mono', monospace; font-size: 11px; color: {C['ink3']}; margin-top: 4px; }}
.bar {{ display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 8px; background: {C['rule']}; }}
.bar i {{ display: block; height: 100%; }}
@media (max-width: 720px) {{ .cards {{ grid-template-columns: minmax(0, 1fr); }} }}
.stTabs [data-baseweb="tab"] p {{ font-family: 'Young Serif', serif; font-size: 19px; }}
[data-testid="stCaptionContainer"] {{ color: {C['ink3']}; }}
</style>
""", unsafe_allow_html=True)


def bar(parts, total):
    return '<div class="bar">' + "".join(f'<i style="width:{n / total * 100:.2f}%;background:{c}"></i>' for n, c in parts) + "</div>"


def senate_totals(res):
    s = res["senate"]
    won = {p: sum(1 for r in s if r["status"] == p) for p in ("D", "R", "I")}
    return (res["senate_holdovers"]["D"] + won["D"], res["senate_holdovers"]["R"] + won["R"], won["I"],
            sum(1 for r in s if r["status"] == "open"))


def can_edit() -> bool:
    """Labeling, classifying and rebuilding only work when the app runs on your own computer.

    On a hosted copy (Streamlit Community Cloud) every visitor would be spending your API key, and
    files saved there are wiped when the app restarts, so the hosted app is read-only. Set
    MIDTERMS_EDIT=1 to force editing on, for example in tests.
    """
    if os.environ.get("MIDTERMS_EDIT") == "1":
        return True
    try:
        host = st.context.headers.get("Host") or ""
    except Exception:
        host = ""
    return host.rsplit(":", 1)[0] in ("localhost", "127.0.0.1", "[::1]")


EDIT = can_edit()


def get_client():
    if not EDIT:
        raise RuntimeError("Classifying is turned off on the hosted app.")
    key = os.environ.get("ANTHROPIC_API_KEY")
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", key)
    except Exception:  # no secrets.toml
        pass
    # With no key, the SDK still finds an `ant auth login` profile if there is one.
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def names(labels):
    if not labels:
        return ""
    on = [n for k, n in classifier.LABELS if labels.get(k) == 1]
    return ", ".join(on) or "None"


results = store.load_results()
if "flash" in st.session_state:  # a message from before the last rerun
    st.toast(st.session_state.pop("flash"))
d, r, i, u = senate_totals(results)
h, g = results["house"], results["governors"]

# --- Masthead ---------------------------------------------------------------
st.markdown(
    f'<div class="masthead"><div class="eyebrow">2026 U.S. midterms · as of {results["as_of_label"]}</div>'
    '<h1>Midterms 101 · Workbench</h1>'
    '<p class="lede">The results behind the guide, a labeler for <span class="w-now">statements that challenge the count</span>, '
    'and the button that rebuilds the page. Labels a person has checked are the only ones that reach readers.</p></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="cards">'
    f'<div class="card"><div class="name">Senate</div><div class="big"><span class="w-d">{d} D</span> · <span class="w-r">{r} R</span></div>'
    f'<div class="sub">{u} uncalled · 51 for control</div>{bar([(d, C["D"]), (u, C["ink3"]), (r, C["R"])], 100)}</div>'
    f'<div class="card"><div class="name">House</div><div class="big"><span class="w-d">{h["D"]} D</span> · <span class="w-r">{h["R"]} R</span></div>'
    f'<div class="sub">{h["uncalled"]} uncalled · 218 for control</div>{bar([(h["D"], C["D"]), (h["uncalled"], C["ink3"]), (h["R"], C["R"])], 435)}</div>'
    f'<div class="card"><div class="name">Governors</div><div class="big"><span class="w-d">{g["D"]} D</span> · <span class="w-r">{g["R"]} R</span></div>'
    f'<div class="sub">{g["uncalled"]} uncalled · {len(g["flips"])} flipped to Democrats</div>{bar([(g["D"], C["D"]), (g["uncalled"], C["ink3"]), (g["R"], C["R"])], 50)}</div>'
    "</div>",
    unsafe_allow_html=True,
)

tab_page, tab_races, tab_label, tab_publish = st.tabs(["The results", "Senate races", "Label statements", "Publish"])

# --- The results (the page's Part 2, embedded) ---------------------------------
with tab_page:
    page = build_page.render().replace(
        "<title>", '<script>document.documentElement.classList.add("embed")</script><title>', 1)
    components.html(page, height=1500, scrolling=True)
    st.caption("Part 2 of the page, drawn from data/results.json and the statements you've verified. "
               "It updates as soon as you save labels; the published page updates when you rebuild and republish it.")

# --- Senate races ----------------------------------------------------------------
with tab_races:
    rows = []
    for x in results["senate"]:
        m = x["alt_pct"] - x["r_pct"]
        rows.append({
            "State": x["name"],
            "Held by": x["held_by"],
            "Result": "Counting" if x["status"] == "open" else f"{x['status']} win",
            "Flip": x["status"] != "open" and x["status"] != x["held_by"],
            "Challenger": f"{x['alt_candidate']} ({x['alt_party']})",
            "Challenger %": x["alt_pct"],
            "Republican": x["r_candidate"],
            "Republican %": x["r_pct"],
            "2026 margin": round(m, 1),
            "2024 pres. margin": x["pres_2024"],
            "Shift": round(m - x["pres_2024"], 1) if x["alt_party"] == "D" else None,
            "Counted %": x["counted_pct"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "Flip": st.column_config.CheckboxColumn(),
        "2026 margin": st.column_config.NumberColumn(help="Challenger minus Republican, in points"),
        "2024 pres. margin": st.column_config.NumberColumn(help="Harris minus Trump, approximate"),
        "Shift": st.column_config.NumberColumn(help="2026 margin minus 2024 margin. Blank where the challenger was an independent."),
    })

    st.subheader("2024 presidential margin vs. 2026 Senate margin")
    dem = [x for x in results["senate"] if x["alt_party"] == "D"]
    fig = go.Figure()
    lim = 50
    fig.add_shape(type="line", x0=-lim, y0=-lim, x1=lim, y1=lim, line=dict(color=C["ink3"], dash="dot", width=1))
    fig.add_shape(type="line", x0=-lim, y0=0, x1=lim, y1=0, line=dict(color=C["rule"], width=1))
    for party in ("D", "R", "open"):
        pts = [x for x in dem if (x["status"] == party)]
        if not pts:
            continue
        color = C["ink2"] if party == "open" else C[party]
        fig.add_trace(go.Scatter(
            x=[x["pres_2024"] for x in pts], y=[x["alt_pct"] - x["r_pct"] for x in pts],
            mode="markers+text", text=[x["st"] for x in pts], textposition="top center",
            textfont=dict(color=C["ink3"], size=10),
            marker=dict(size=11, color=color if party != "open" else "rgba(0,0,0,0)", line=dict(color=color, width=2)),
            name={"D": "Democrat won", "R": "Republican won", "open": "Still counting"}[party],
            hovertemplate="%{text}: 2024 %{x:+.1f}, 2026 %{y:+.1f}<extra></extra>",
        ))
    fig.update_layout(
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"], font=dict(color=C["ink2"], family="DM Sans"), height=520,
        margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.04, x=0),
        xaxis=dict(title="2024 presidential margin (D − R)", range=[-lim, lim], gridcolor=C["rule"], zeroline=False),
        yaxis=dict(title="2026 Senate margin (D − R)", range=[-lim, lim], gridcolor=C["rule"], zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})
    st.caption("Dots above the dotted line ran ahead of Harris's 2024 margin. Idaho, Montana, Nebraska and South Dakota "
               "are left out because the main challenger was an independent.")

# --- Label statements ----------------------------------------------------------
with tab_label:
    rows = store.load_statements()
    if not EDIT:
        st.info("Labeling is turned off on the hosted app, so nobody can spend the API key or change the labels. "
                "Run the app on your own computer to add, classify and verify statements, then push data/statements.json.")
        public = [x for x in rows if x.get("verified") and x.get("human") and not x.get("fictional")]
        if public:
            st.dataframe(pd.DataFrame([{"Statement": x["text"], "Speaker": x.get("speaker", ""), "Race": x.get("race", ""),
                                        "Labels (checked by a person)": names(x["human"]), "Claude said": names(x["claude"])}
                                       for x in public]), hide_index=True, width="stretch")
        else:
            st.caption("No real statements have been verified yet.")
    else:
        st.subheader("1 · Add statements")
        a, b = st.columns(2)
        with a:
            up = st.file_uploader("CSV with a text column (speaker, kind, race, date, url optional)", type="csv")
            if up is not None and st.button("Add from CSV"):
                try:
                    rows, n = store.merge(rows, store.parse_csv(up.getvalue()))
                    store.save_statements(rows)
                    st.success(f"Added {n} statement{'s' if n != 1 else ''}.")
                except ValueError as e:
                    st.error(str(e))
            if st.button("Add the 7 fictional examples to practice on"):
                ex = [{**store.new_statement(text=e["text"], kind=e["kind"]), "fictional": True, "human": e["human"]}
                      for e in store.load_examples()]
                rows, n = store.merge(rows, ex)
                store.save_statements(rows)
                st.success(f"Added {n}. They come with hand labels and never reach the page.")
        with b:
            with st.form("one", clear_on_submit=True):
                text = st.text_area("Or paste one statement")
                c1, c2 = st.columns(2)
                speaker, kind = c1.text_input("Speaker"), c2.text_input("Kind", placeholder="Campaign post, speech…")
                race, date = c1.text_input("Race", placeholder="MS Senate"), c2.text_input("Date", placeholder="2026-11-08")
                url = st.text_input("Source URL")
                if st.form_submit_button("Add") and text.strip():
                    rows, n = store.merge(rows, [store.new_statement(text=text, speaker=speaker, kind=kind, race=race, date=date, url=url)])
                    store.save_statements(rows)
                    st.success("Added." if n else "That statement is already in the set.")

        st.subheader("2 · Classify")
        pending = [x for x in rows if not x.get("claude")]
        runs = st.radio("Runs per statement", [1, 3, 5], index=1, horizontal=True)
        st.caption(f"Each statement runs {runs} time{'s' if runs != 1 else ''} on {classifier.MODEL}. "
                   "A label that changes between runs is flagged for you to check.")
        if st.button(f"Classify {len(pending)} new statement{'s' if len(pending) != 1 else ''}", disabled=not pending, type="primary"):
            client = get_client()
            prog = st.progress(0.0)
            for n, x in enumerate(pending, 1):
                try:
                    x.update(classifier.classify_repeated(client, x["text"], runs=runs))
                except classifier.Refused as e:
                    x.update(rule_problems=[f"Claude declined: {e}"])
                    st.warning(f"Claude declined one statement: {x['text'][:80]}…")
                except anthropic.AuthenticationError:
                    st.error("No working Anthropic API key. Add ANTHROPIC_API_KEY to .streamlit/secrets.toml (see secrets.toml.example).")
                    break
                except anthropic.RateLimitError:
                    st.error("Rate limited. The ones done so far are saved; wait a minute and classify the rest.")
                    break
                except anthropic.APIStatusError as e:
                    st.error(f"API error {e.status_code}: {e.message}")
                    break
                except anthropic.APIConnectionError:
                    st.error("Couldn't reach the Anthropic API. Check your connection.")
                    break
                store.save_statements(rows)
                prog.progress(n / len(pending))
            else:
                st.session_state["flash"] = f"Classified {len(pending)} statement{'s' if len(pending) != 1 else ''}."
                st.rerun()

        st.subheader("3 · Check the labels")
        done = [x for x in rows if x.get("claude")]
        if not done:
            st.info("Nothing classified yet.")
        else:
            flagged = sum(1 for x in done if x.get("unstable") or x.get("rule_problems"))
            st.caption(f"{len(done)} classified · {flagged} flagged · {sum(1 for x in done if x.get('verified'))} verified. "
                       "Ticks start at Claude's labels. Fix any that are wrong, tick Verified, then save. "
                       "Only verified real statements go to the page.")
            table = pd.DataFrame([{
                "id": x["id"],
                "Statement": x["text"],
                "Speaker": x.get("speaker", ""),
                "Claude says": names(x["claude"]),
                "Check": "; ".join(([f"changed between runs: {', '.join(x['unstable'])}"] if x.get("unstable") else [])
                                   + list(x.get("rule_problems") or [])),
                **{n: bool((x.get("human") or x["claude"]).get(k)) for k, n in classifier.LABELS},
                "Verified": bool(x.get("verified")),
                "Fictional": bool(x.get("fictional")),
                "Remove": False,
            } for x in done])
            edited = st.data_editor(
                table, hide_index=True, width="stretch", key="editor",
                disabled=["id", "Statement", "Speaker", "Claude says", "Check", "Fictional"],
                column_config={"id": None, "Statement": st.column_config.TextColumn(width="large"),
                               "Check": st.column_config.TextColumn(width="medium")},
            )
            if st.button("Save labels", type="primary"):
                byid = {x["id"]: x for x in rows}
                drop = set()
                for _, e in edited.iterrows():
                    x = byid[e["id"]]
                    if e["Remove"]:
                        drop.add(x["id"])
                        continue
                    x["human"] = {k: int(e[n]) for k, n in classifier.LABELS}
                    x["verified"] = bool(e["Verified"])
                rows = [x for x in rows if x["id"] not in drop]
                store.save_statements(rows)
                st.session_state["flash"] = "Labels saved."
                st.rerun()

    done = [x for x in rows if x.get("claude")]
    st.subheader("How often Claude agrees with a person")
    checked = [x for x in done if x.get("verified") and x.get("human")]
    if not checked:
        st.caption("Verify some statements to see agreement.")
    else:
        agree = pd.DataFrame([{
            "Label": n,
            "Agree": f"{sum(x['claude'][k] == x['human'][k] for x in checked) / len(checked):.0%}",
            "Claude 1, you 0": sum(x["claude"][k] == 1 and x["human"][k] == 0 for x in checked),
            "Claude 0, you 1": sum(x["claude"][k] == 0 and x["human"][k] == 1 for x in checked),
        } for k, n in classifier.LABELS])
        st.dataframe(agree, hide_index=True, width="stretch")
        st.caption(f"Over {len(checked)} verified statement{'s' if len(checked) != 1 else ''}. "
                   "Read every disagreement before trusting the counts.")

    with st.expander("The prompt Claude gets"):
        st.code(classifier.RULES, language=None, wrap_lines=True)

# --- Publish ---------------------------------------------------------------------
with tab_publish:
    shown = store.for_page(store.load_statements())
    real = bool(shown) and not shown[0].get("fictional")
    st.markdown(f"The page will show **{len(shown)} {'verified real statements' if real else 'fictional examples'}**"
                f"{'' if real else ' (no real statements are verified yet)'}.")
    for p in build_page.check(results):
        st.warning(p)
    if EDIT and st.button("Rebuild page/index.html", type="primary"):
        html = build_page.render()
        (build_page.PAGE / "index.html").write_text(html, encoding="utf-8")
        st.success(f"Wrote page/index.html ({len(html):,} bytes).")
    st.download_button("Download the page", build_page.render(), file_name="index.html", mime="text/html")
    st.caption("To update the published Midterms 101 artifact, ask Claude to republish page/index.html to it. "
               "The prose in Parts 1 and 3 is written by hand in page/template.html and doesn't follow the data.")
