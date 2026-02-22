# Worldlines

An autonomous research system that interprets new physics findings through a computational framework for reality.

## What This Is

Worldlines is a self-running system. Every day, it:

1. Fetches recent physics papers from ArXiv (high-energy theory, general relativity, quantum physics, statistical mechanics)
2. Selects papers — 2 most likely to *strain* the framework, 1 most likely to offer genuine *validation*
3. Interprets those papers through the Worldlines computational framework, which holds that reality is literally computation built from five primitives: discrete ticks, gradient fields, attractors, resolution events, and conservation of computation
4. Updates its living model of reality based on what it finds
5. Tracks unresolved tensions — places where the framework fails, strains, or produces surprising descriptions

The system commits its outputs to this repository. **The git history is the arrow of time** — each commit is a resolved tick, an irreversible state update.

## What To Read

- **[state/model.md](state/model.md)** — The system's current model of reality. This is a living document that evolves with each cycle. The original seed content stays intact; updates are appended as dated sections.
- **[tensions/open.md](tensions/open.md)** — Unresolved states. Things the framework cannot yet account for. New tensions are added when cycles generate them. Tensions are only removed when they resolve into the state layer or are demonstrated to be malformed questions.
- **[cycles/](cycles/)** — One file per cycle. Each contains the full interpretive output: which papers were processed, where the framework strained, what changed, and the system's self-assessment.

## What This Is Not

This system is not trying to prove the Worldlines framework correct. It is stress-testing the framework against real physics research. Comfortable coherence is failure. Productive tension is success. The interesting outputs are the places where the framework breaks or bends in unexpected ways.

## How It Runs

The system runs daily at 06:00 UTC via GitHub Actions. It can also be triggered manually from the Actions tab. The interpretive engine is Claude (claude-opus-4-6), called via the Anthropic API with a system prompt that instructs it to prioritize honesty about the framework's limits over smooth narrative.

## Architecture

```
agent/run.py            — The main agent script (fetch, select, interpret, score, update)
state/model.md          — Living document: the system's current model
tensions/open.md        — Unresolved tensions the system is tracking
cycles/YYYY-MM-DD.md    — Per-cycle output files
scoring/scores.jsonl    — Accumulated strain/validation scores (one JSON object per paper)
scoring/visualize.html  — Interactive D3.js visualization of the score distribution
.github/workflows/      — GitHub Actions scheduling
```

## Setup

1. Fork or clone this repository
2. Add your `ANTHROPIC_API_KEY` as a repository secret (Settings > Secrets and variables > Actions)
3. The workflow runs daily, or trigger it manually from the Actions tab

## Scoring

After each interpretive cycle, every paper is scored on two dimensions (0-10 each):

- **Strain** — How much the paper resists interpretation through the Worldlines framework. 0 = trivially handled. 5 = real tension exists. 10 = the framework cannot coherently account for the finding.
- **Validation** — How specifically the paper validates the framework — not just consistency, but predictive purchase. 0 = merely consistent (post-hoc fit). 5 = the framework's lens emphasizes something this paper confirms. 10 = the framework clearly predicted this in a way conventional physics did not.

**Validation threshold rule:** Scores above 3 require articulable predictive specificity. If the scorer cannot state what the framework predicted in advance, the validation score must be 3 or below. "Consistent with" is not validation.

Scores accumulate in `scoring/scores.jsonl` — one JSON line per paper per cycle. The visualization at `scoring/visualize.html` renders the distribution as a scatter plot with quadrant analysis.

## Visualization

The file `scoring/visualize.html` is a self-contained D3.js page that loads `scores.jsonl` and renders:

- **Scatter plot**: strain (x) vs validation (y), with quadrant lines at 5/5 and labels (Productive friction, Genuine confirmation, Hard resistance, Neutral territory)
- **Time series**: average strain and validation per cycle date, showing distribution drift
- **Stats panel**: totals, averages, quadrant counts, most strained paper, best validation

To view it:

1. **Locally**: Clone the repo and open `scoring/visualize.html` in a browser. It fetches `scores.jsonl` via relative path, so it works from the filesystem or any local server.
2. **GitHub Pages**: Go to Settings > Pages > deploy from main branch. The visualization will be available at `https://<username>.github.io/<repo>/scoring/visualize.html`.

## License

This repository is a research artifact. The framework, the agent's outputs, and the tension tracking are all part of an ongoing autonomous inquiry.
