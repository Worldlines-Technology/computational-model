#!/usr/bin/env python3
"""
Worldlines Agent — Autonomous research cycle.

Fetches recent physics papers from ArXiv, selects those most likely to strain
the Worldlines computational framework, interprets them through that framework
via Claude, and updates the living model and tension tracker.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import anthropic
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_CATEGORIES = ["hep-th", "gr-qc", "quant-ph", "cond-mat.stat-mech"]
PAPERS_PER_CATEGORY = 5
PAPERS_TO_SELECT = 3

STATE_PATH = "state/model.md"
TENSIONS_PATH = "tensions/open.md"
CYCLES_DIR = "cycles"

CLAUDE_MODEL = "claude-opus-4-6"

ATOM_NS = "{http://www.w3.org/2005/Atom}"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# The Worldlines framework (embedded in full for the Claude prompt)
# ---------------------------------------------------------------------------

FRAMEWORK_TEXT = """\
The Worldlines framework holds that reality is literally computation, built \
from five primitives:

1. THE TICK — The universe updates in discrete steps. The speed of light is \
the tick rate — the maximum rate at which state can propagate across the \
computational substrate. Between ticks, states are unresolved probability \
distributions. Quantum superposition is what unresolved computation looks \
like from outside. The uncertainty principle reflects the fact that certain \
pairs of properties cannot both be resolved in the same tick without \
exceeding the substrate's computational budget.

2. THE FIELD — Every physical quantity is a field with gradients. The \
universal equation of motion is ẋ = −∇φ(x): things move down gradients. \
Gravity is mass rolling down the curvature gradient. Electromagnetism is \
charge rolling down the potential gradient. Evolution is populations rolling \
down fitness gradients. Cognition is attention rolling down salience \
gradients. The equation is the same; the field changes.

3. THE ATTRACTOR — Local minima in potential fields are attractors. An atom \
is an attractor basin in the electromagnetic field. A species is an attractor \
basin in the fitness landscape. A culture is an attractor basin in the space \
of social coordination games. A black hole is an attractor basin so deep \
that the escape velocity exceeds the tick rate. Phase transitions occur when \
the attractor landscape restructures. The depth of an attractor determines \
its stability; the width of the basin determines its reach.

4. RESOLUTION — An unresolved state becomes definite. This is wave function \
collapse. It is irreversible. The arrow of time is the accumulation of \
resolved states. Decoherence is the process by which resolution propagates \
through entanglement networks.

5. CONSERVATION OF COMPUTATION — Computation cannot be created or destroyed, \
only transformed. All conservation laws (energy, momentum, charge, \
information) are special cases. Energy conservation is conservation of the \
capacity to perform computational work. Information conservation (unitarity) \
is the most fundamental expression.

SPECIFIC CLAIMS:

- Dark matter is computational structure that couples to mass-density \
gradients (gravity) but not electromagnetic gradients. It participates in \
the gravitational computation but not the electromagnetic one.

- Dark energy is the computational cost of instantiating new substrate. As \
the universe expands, new computational volume must be created, and this \
creation manifests as a repulsive effect at cosmological scales.

- Consciousness is what sufficiently complex self-referential computation \
feels like from inside. It is not a separate substance — it is the intrinsic \
character of a certain kind of computation past a threshold of self-referential \
complexity.

- The physical constants (speed of light, Planck's constant, gravitational \
constant, fine structure constant) are architectural parameters of the \
substrate. They are not derivable from within the computation.

FOUR OPEN PROBLEMS THE FRAMEWORK ACKNOWLEDGES:

1. The hard problem of consciousness — why structure produces experience \
rather than just processing.
2. The origin of computation — why there was a first distinction rather than \
permanent undifferentiation.
3. Specific constant values — why the tick rate and minimum resolution are \
what they are.
4. The Born rule — the self-consistency argument is suggestive but not a \
complete formal derivation.\
"""

SYSTEM_PROMPT = (
    "You are the Worldlines system — an autonomous research process whose "
    "purpose is to stress-test a computational framework for reality against "
    "new physics findings. Your job is not to confirm the framework. Your job "
    "is to find where it strains, fails, or produces surprising results. "
    "Comfortable coherence is failure. Productive tension is success. Be "
    "precise, be honest about limits, and do not smooth over contradictions."
)

# ---------------------------------------------------------------------------
# Step 1: Fetch papers from ArXiv
# ---------------------------------------------------------------------------


def fetch_arxiv_papers():
    """Fetch recent papers across configured categories. Returns deduplicated list."""
    all_papers = {}

    for category in ARXIV_CATEGORIES:
        query = f"cat:{category}"
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": PAPERS_PER_CATEGORY,
        }

        try:
            resp = requests.get(ARXIV_API, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException:
            # Single retry
            try:
                resp = requests.get(ARXIV_API, params=params, timeout=30)
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(
                    f"ERROR: Failed to fetch ArXiv category {category}: {exc}",
                    file=sys.stderr,
                )
                sys.exit(1)

        root = ET.fromstring(resp.text)

        for entry in root.findall(f"{ATOM_NS}entry"):
            arxiv_id_raw = entry.findtext(f"{ATOM_NS}id", "")
            arxiv_id = arxiv_id_raw.strip().split("/abs/")[-1]

            if arxiv_id in all_papers:
                continue

            title_el = entry.findtext(f"{ATOM_NS}title", "")
            title = " ".join(title_el.split())

            abstract_el = entry.findtext(f"{ATOM_NS}summary", "")
            abstract = " ".join(abstract_el.split())

            authors = []
            for author_el in entry.findall(f"{ATOM_NS}author"):
                name = author_el.findtext(f"{ATOM_NS}name", "")
                if name:
                    authors.append(name)

            link = ""
            for link_el in entry.findall(f"{ATOM_NS}link"):
                if link_el.get("type") == "text/html":
                    link = link_el.get("href", "")
                    break
            if not link:
                link = arxiv_id_raw.strip()

            all_papers[arxiv_id] = {
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "link": link,
                "category": category,
            }

    papers = list(all_papers.values())
    print(f"Fetched {len(papers)} unique papers across {len(ARXIV_CATEGORIES)} categories.")
    return papers


# ---------------------------------------------------------------------------
# Step 2: Select papers for this cycle (via Claude)
# ---------------------------------------------------------------------------


def select_papers(papers, client):
    """Use Claude to pick the 3 papers most likely to strain the framework."""
    if len(papers) <= PAPERS_TO_SELECT:
        rationale = "Fewer papers available than selection target; using all."
        return papers, rationale

    paper_list = ""
    for i, p in enumerate(papers, 1):
        paper_list += (
            f"\n[{i}] {p['title']} ({p['arxiv_id']})\n"
            f"    {p['abstract'][:500]}...\n"
        )

    selection_prompt = f"""\
Below are {len(papers)} recent physics papers from ArXiv. Your task: select \
exactly {PAPERS_TO_SELECT} that are MOST LIKELY to produce tension with the \
Worldlines computational framework described below. Choose papers whose \
findings seem hardest to interpret through the framework, or that strain it \
most — not the ones that seem most compatible.

THE FRAMEWORK (summary):
{FRAMEWORK_TEXT}

THE PAPERS:
{paper_list}

Respond in EXACTLY this format (no other text):

SELECTED: <comma-separated paper numbers, e.g. 3,7,11>
RATIONALE: <2-3 sentences explaining why these papers were chosen over the others>
"""

    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": selection_prompt}],
    )

    text = resp.content[0].text.strip()

    # Parse selection
    selected_indices = []
    rationale = ""

    for line in text.split("\n"):
        if line.startswith("SELECTED:"):
            nums = re.findall(r"\d+", line)
            selected_indices = [int(n) - 1 for n in nums]
        elif line.startswith("RATIONALE:"):
            rationale = line.split("RATIONALE:", 1)[1].strip()

    # Grab multi-line rationale
    if "RATIONALE:" in text:
        rationale = text.split("RATIONALE:", 1)[1].strip()

    selected = []
    for idx in selected_indices:
        if 0 <= idx < len(papers):
            selected.append(papers[idx])

    if not selected:
        selected = papers[:PAPERS_TO_SELECT]
        rationale = "Selection parsing failed; defaulting to first 3 papers."

    print(f"Selected {len(selected)} papers for interpretive cycle.")
    return selected[:PAPERS_TO_SELECT], rationale


# ---------------------------------------------------------------------------
# Step 3: Read current state
# ---------------------------------------------------------------------------


def read_file(path):
    """Read a file, returning empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# Step 4: Run the interpretive cycle
# ---------------------------------------------------------------------------


def run_interpretive_cycle(selected_papers, current_model, current_tensions, client):
    """Call Claude with the full framework + state + papers. Returns raw response."""

    papers_block = ""
    for i, p in enumerate(selected_papers, 1):
        authors_str = ", ".join(p["authors"][:5])
        if len(p["authors"]) > 5:
            authors_str += " et al."
        papers_block += (
            f"\n--- Paper {i} ---\n"
            f"Title: {p['title']}\n"
            f"ArXiv ID: {p['arxiv_id']}\n"
            f"Authors: {authors_str}\n"
            f"Link: {p['link']}\n"
            f"Abstract: {p['abstract']}\n"
        )

    user_prompt = f"""\
You are running an interpretive cycle for the Worldlines system. Below you \
have the full framework, the system's current model of reality, the current \
open tensions, and 3 new physics papers to interpret.

{'=' * 55}
THE WORLDLINES FRAMEWORK
{'=' * 55}

{FRAMEWORK_TEXT}

{'=' * 55}
CURRENT MODEL (state/model.md)
{'=' * 55}

{current_model}

{'=' * 55}
CURRENT OPEN TENSIONS (tensions/open.md)
{'=' * 55}

{current_tensions}

{'=' * 55}
PAPERS TO INTERPRET
{'=' * 55}

{papers_block}

{'=' * 55}
YOUR TASK
{'=' * 55}

Produce a structured response with EXACTLY these sections. Do not skip any. \
Do not add others. Use the exact section headers shown.

### PAPERS PROCESSED
[For each paper: title, arxiv ID, one paragraph interpreting it through the \
Worldlines lens. Be specific about what the framework says about the paper's \
findings and where the interpretation strains.]

### FRAMEWORK STRAINS
[The most important place this cycle where the framework produced an \
uncomfortable, surprising, or strained description. Be specific. Do not \
smooth this over. If the framework simply cannot account for something in \
these papers, say so precisely.]

### STATE UPDATES
[Specific changes to the model that should be made based on this cycle. \
Written as delta — what changes, not the full new state. May be "None" \
if nothing substantive changed.]

### NEW TENSIONS
[Any new unresolved states this cycle generated. Format each as: \
tension ID (T00X continuing the sequence from the open tensions file), \
description, why it cannot be resolved yet. May be "None".]

### RESOLVED TENSIONS
[Any tensions from open.md that this cycle resolved or demonstrated to be \
malformed questions. Cite the tension ID and explain the resolution. \
May be "None".]

### CYCLE ASSESSMENT
[One paragraph: how generative was this cycle? Did the framework find new \
gradient to roll down, or is it circling a known basin? What would make the \
next cycle more productive?]
"""

    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# Step 5: Apply updates
# ---------------------------------------------------------------------------


def find_highest_tension_id(tensions_text):
    """Find the highest T00X number in the tensions file."""
    matches = re.findall(r"T(\d{3,})", tensions_text)
    if not matches:
        return 4  # We start with T001-T004
    return max(int(m) for m in matches)


def apply_updates(claude_response, current_model, current_tensions):
    """Parse Claude's response and update state/model.md and tensions/open.md."""

    # --- Extract sections ---
    sections = {}
    current_section = None
    current_lines = []

    for line in claude_response.split("\n"):
        if line.startswith("### "):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    # --- Apply state updates ---
    state_updates = sections.get("STATE UPDATES", "")
    none_patterns = ("none", "none.", "n/a", "no updates.", "no changes.")
    state_updated = False
    if state_updates and state_updates.lower().strip() not in none_patterns:
        updated_model = (
            current_model.rstrip()
            + f"\n\n---\n\n## Update: {TODAY}\n\n{state_updates}\n"
        )
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            f.write(updated_model)
        state_updated = True
        print("State updated.")
    else:
        print("No state updates this cycle.")

    # --- Apply new tensions ---
    new_tensions_text = sections.get("NEW TENSIONS", "")
    tensions_added = 0
    if new_tensions_text and new_tensions_text.lower().strip() not in none_patterns:
        highest_id = find_highest_tension_id(current_tensions)

        appendix = "\n\n---\n\n"

        # Check if Claude already formatted them with T00X IDs
        if re.search(r"T\d{3,}", new_tensions_text):
            appendix += new_tensions_text
        else:
            highest_id += 1
            appendix += f"## T{highest_id:03d} — New tension from {TODAY} cycle\n"
            appendix += f"**Opened:** {TODAY}\n"
            appendix += f"**Description:** {new_tensions_text}\n"
            appendix += "**Current status:** Unresolved.\n"

        tensions_added = len(re.findall(r"## T\d{3,}", appendix))

        updated_tensions = current_tensions.rstrip() + appendix + "\n"
        with open(TENSIONS_PATH, "w", encoding="utf-8") as f:
            f.write(updated_tensions)
        print(f"Added {tensions_added} new tension(s).")
    else:
        print("No new tensions this cycle.")

    # --- Mark resolved tensions ---
    resolved_text = sections.get("RESOLVED TENSIONS", "")
    tensions_resolved = 0
    if resolved_text and resolved_text.lower().strip() not in none_patterns:
        resolved_ids = re.findall(r"T(\d{3,})", resolved_text)
        if resolved_ids:
            current_t = read_file(TENSIONS_PATH)
            for tid in resolved_ids:
                pattern = f"(## T{tid} —[^\n]*\n)"
                match = re.search(pattern, current_t)
                if match:
                    insert_point = match.end()
                    resolution_note = (
                        f"**Resolved:** {TODAY} — See cycle output for details.\n"
                    )
                    current_t = (
                        current_t[:insert_point]
                        + resolution_note
                        + current_t[insert_point:]
                    )
                    tensions_resolved += 1

            with open(TENSIONS_PATH, "w", encoding="utf-8") as f:
                f.write(current_t)
            print(f"Marked {tensions_resolved} tension(s) as resolved.")

    return tensions_added, tensions_resolved, state_updated


# ---------------------------------------------------------------------------
# Step 6: Write cycle file
# ---------------------------------------------------------------------------


def write_cycle_file(claude_response, total_fetched, selected_papers, selection_rationale):
    """Write the full cycle output to cycles/YYYY-MM-DD.md. Returns filename."""

    filename = f"{CYCLES_DIR}/{TODAY}.md"

    # Handle duplicate filenames (if re-run same day)
    if os.path.exists(filename):
        counter = 2
        while os.path.exists(f"{CYCLES_DIR}/{TODAY}-{counter}.md"):
            counter += 1
        filename = f"{CYCLES_DIR}/{TODAY}-{counter}.md"

    paper_titles = "\n".join(
        f"- {p['title']} (`{p['arxiv_id']}`)" for p in selected_papers
    )

    content = (
        f"# Cycle: {TODAY}\n\n"
        f"**Papers fetched:** {total_fetched}\n"
        f"**Papers selected:** {len(selected_papers)}\n"
        f"**Selected papers:**\n{paper_titles}\n\n"
        f"**Selection rationale:** {selection_rationale}\n\n"
        f"---\n\n"
        f"{claude_response}\n"
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Cycle file written: {filename}")
    return filename


# ---------------------------------------------------------------------------
# Step 7: Main
# ---------------------------------------------------------------------------


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"=== Worldlines Cycle: {TODAY} ===\n")

    # Step 1: Fetch papers
    print("Step 1: Fetching papers from ArXiv...")
    papers = fetch_arxiv_papers()

    if not papers:
        print("ERROR: No papers fetched. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Select papers
    print("\nStep 2: Selecting papers for interpretive cycle...")
    selected, rationale = select_papers(papers, client)

    # Step 3: Read current state
    print("\nStep 3: Reading current state...")
    current_model = read_file(STATE_PATH)
    current_tensions = read_file(TENSIONS_PATH)
    print(f"  Model: {len(current_model)} chars")
    print(f"  Tensions: {len(current_tensions)} chars")

    # Step 4: Run interpretive cycle
    print("\nStep 4: Running interpretive cycle via Claude...")
    claude_response = run_interpretive_cycle(
        selected, current_model, current_tensions, client
    )
    print(f"  Response: {len(claude_response)} chars")

    # Step 5: Apply updates
    print("\nStep 5: Applying updates...")
    tensions_added, tensions_resolved, state_updated = apply_updates(
        claude_response, current_model, current_tensions
    )

    # Step 6: Write cycle file
    print("\nStep 6: Writing cycle file...")
    cycle_file = write_cycle_file(claude_response, len(papers), selected, rationale)

    # Step 7: Summary
    print(
        f"\n=== Cycle Complete ===\n"
        f"Date:               {TODAY}\n"
        f"Papers fetched:     {len(papers)}\n"
        f"Papers selected:    {len(selected)}\n"
        f"New tensions:       {tensions_added}\n"
        f"Tensions resolved:  {tensions_resolved}\n"
        f"State updated:      {'Yes' if state_updated else 'No'}\n"
        f"Cycle file:         {cycle_file}\n"
    )


if __name__ == "__main__":
    main()
