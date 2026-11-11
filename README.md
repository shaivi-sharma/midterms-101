# Midterms 101

A beginner's guide to the 2026 U.S. midterms, plus the Streamlit workbench behind it. It has the same setup as `economy-vs-your-economy`:

- **The page** (`page/`) is *Midterms 101*: a static, self-contained guide in three parts (the basics, the results, what it means). `build_page.py` writes its data into `page/template.html` and saves the result as `page/index.html`, the file that's published as the artifact.
- **The workbench** (`app.py`) is a Streamlit app with four tabs:
  - **The results**: Part 2 of the page, embedded.
  - **Senate races**: a sortable table and a chart of each state's 2024 presidential margin against its 2026 Senate margin.
  - **Label statements**: runs the election-statement classifier on real statements, flags labels that change between runs, and lets a person correct and verify them.
  - **Publish**: rebuilds the page.

Only statements a person has verified reach the page. Until then, its Statements tab shows the seven fictional examples.

## Run the workbench

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your ANTHROPIC_API_KEY
.venv/bin/streamlit run app.py
```

The key is only needed for the **Label statements** tab. `secrets.toml` is git-ignored.

## Editing only works on your computer

Adding, classifying and verifying statements, and rebuilding the page, only work when you open the app at `localhost`. Anywhere else, including a hosted copy or your network address, the app is read-only: it shows the results, the verified statements and the agreement table, with no buttons. There are two reasons:

- On a public app, every visitor who clicks Classify would spend your API key.
- Streamlit Community Cloud wipes saved files when the app restarts, so labels saved there would be lost.

**The workflow:**
1. Label on your computer.
2. Commit `data/statements.json`.
3. Push.

The hosted app redeploys with the new labels. Setting `MIDTERMS_EDIT=1` forces editing on, for example in tests.

## Deploy (Streamlit Community Cloud)

1. Create an empty repo at github.com/new (no README, no .gitignore).
2. Push the project:
   ```bash
   git init && git add . && git status   # secrets.toml and .venv must NOT be listed
   git commit -m "Midterms 101 page and workbench" && git branch -M main
   git remote add origin https://github.com/<you>/midterms-101.git && git push -u origin main
   ```
3. At share.streamlit.io, choose **Create app** → **Deploy a public app from GitHub**. Pick the repo, branch `main`, and main file `app.py`.
4. Under **Advanced settings**, choose Python 3.12. **Leave Secrets empty.** The hosted app is read-only, so it never needs your API key.
5. Click **Deploy**. Every later `git push` to `main` redeploys the app.

## How the pieces fit

```
data/results.json ─┐
data/statements.json ─┼─> build_page.py ─> page/index.html  (published as the artifact)
classifier.py RULES ─┘          │
                                └─> app.py "The results" tab (same page, embed mode)
```

- `classifier.py` holds the **only copy of the classifier rules**. The workbench sends them to Claude (`claude-opus-5-5`, low effort, JSON schema output, server-side refusal fallback). The build writes the same rules into the page, so its "Show the prompt" box always matches.
- **Embed mode:** the workbench adds an `embed` class to the page. That hides the masthead, Parts 1 and 3, the footer, and the live "Classify with Claude" box, since that box only works inside the Claude viewer.
- `data/statements.json` is the labeler's working set. Each statement stores Claude's majority labels, every individual run, any labels that changed between runs, rule violations (for example `integrity_challenge` 0 while a source label is 1), a person's labels, and a `verified` flag.

## Updating the results

Edit `data/results.json` or replace it with a feed, then run:

```bash
.venv/bin/python build_page.py
```

The build checks that the Senate totals 100 seats, the House 435, and that the uncalled House list matches its count.

**What the data doesn't update:** the prose in Parts 1 and 3 is written by hand in `page/template.html`. That includes the verdict cards, the stat cards, "Who can do what" and "What to watch next". When a race is called, update that text as well as the JSON. The charts, map, tables and flip lists follow the data on their own.

## Data

AP vote counts as of 9 p.m. ET, Nov. 8, 2026, compiled by the California Today results guide. Race calls were checked against CBS News, and totals against NBC News and KCRA. The results are unofficial until states certify, and the 2024 presidential margins are approximate. The seven example statements are fictional.
