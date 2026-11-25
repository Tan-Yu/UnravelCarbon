"""Runs the six test questions from the brief end to end; saves answers with sources to build/cache/test_questions.md.
Usage: python3 run_tests.py [--model NAME]"""
import sys, json, time
import agent
from agent import Agent
if "--model" in sys.argv: agent.MODEL = sys.argv[sys.argv.index("--model") + 1]
QS = [
 ("Core 1", "Should employee business travel be classified as Scope 1 or Scope 3? Explain the reasoning and describe how I can calculate my business travel emissions?"),
 ("Core 2", "Are my scope 2 emissions calculation valid according to the Greenhouse Gas Protocol?"),
 ("Core 3", "How do my scope 1 & 2 emissions compare with other companies (refer to peer reports in the data sources) in my industry, and what insights can I derive from this comparison?"),
 ("Bonus 1", "What is our highest emitting Scope 3 category and what specific activities contribute to it?"),
 ("Bonus 2", "Which suppliers should I prioritise to engage for emissions reduction efforts?"),
 ("Bonus 3", "Generate a summary report of our total emissions by scope with key insights"),
]
if __name__ == "__main__":
    ag = Agent(); out = ["# Test question answers (model %s, prompt %s)\n" % (agent.MODEL, agent.PROMPT_VERSION)]
    for tag, q in QS:
        r = ag.ask(q)
        print(f"\n##### {tag}: {q}\n{r['answer']}\n-- tools {[t['tool'] for t in r['trace']]} uncited={r['uncited_pages']} in={r['tokens_in']} out={r['tokens_out']} ${r['cost_usd']}")
        out.append(f"## {tag}: {q}\n\n{r['answer']}\n\n**Sources**\n" + "\n".join(f"- [{s['n']}] {s['label']}" for s in r["sources"])
                   + f"\n\n_tools: {[t['tool'] for t in r['trace']]}; {r['tokens_in']} in / {r['tokens_out']} out tokens; ${r['cost_usd']}_\n")
        time.sleep(7)
    open("build/cache/test_questions.md", "w").write("\n".join(out))
