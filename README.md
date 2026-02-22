# Worldlines

An autonomous research system that interprets new physics findings through a computational framework for reality.

## What This Is

Worldlines is a self-running system. Every day, it:

1. Fetches recent physics papers from ArXiv (high-energy theory, general relativity, quantum physics, statistical mechanics)
2. Selects the papers most likely to *strain* its interpretive framework — not confirm it
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
agent/run.py          — The main agent script (fetch, select, interpret, update)
state/model.md        — Living document: the system's current model
tensions/open.md      — Unresolved tensions the system is tracking
cycles/YYYY-MM-DD.md  — Per-cycle output files
.github/workflows/    — GitHub Actions scheduling
```

## Setup

1. Fork or clone this repository
2. Add your `ANTHROPIC_API_KEY` as a repository secret (Settings > Secrets and variables > Actions)
3. The workflow runs daily, or trigger it manually from the Actions tab

## License

This repository is a research artifact. The framework, the agent's outputs, and the tension tracking are all part of an ongoing autonomous inquiry.
