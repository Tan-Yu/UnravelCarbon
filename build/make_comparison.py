"""Builds results/COMPARISON.md: the same six test questions answered by each agent version, side by side per question.
Inputs: results/test_questions/NN_<version>_<model>.(md|txt)."""
import re
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "results"
runs = {}
for f in sorted((R / "test_questions").iterdir()):
    label = f.stem; text = f.read_text()
    # .md files use '## Tag: question'; .txt logs use '##### Tag: question'
    parts = re.split(r"^#{2,5} (Core \d|Bonus \d): ", text, flags=re.M)
    for i in range(1, len(parts), 2):
        q, body = parts[i], parts[i + 1]
        q_text, _, ans = body.partition("\n")
        runs.setdefault(q, dict(question=q_text.strip(), by={}))["by"][label] = ans.strip()
out = ["# Same six questions, every agent version\n",
       "Versions: 01 v2 flash (first agent) | 02 v3 flash (+general prompt rules, data caveats, claim check) | "
       "03 v4 flash (+multi-query search, id filter) | 04 v4 gemini-4-hydrogen (only the model changed).\n",
       "Cost/tokens/tool calls are in each version's `-- tools ...` line. Ledger entries: EXPERIMENTS.md E10-E13.\n"]
for q, d in runs.items():
    out.append(f"\n---\n\n## {q}: {d['question']}\n")
    for label, ans in d["by"].items():
        out.append(f"\n### {label}\n\n{ans}\n")
(R / "COMPARISON.md").write_text("\n".join(out)); print({q: len(d["by"]) for q, d in runs.items()})
