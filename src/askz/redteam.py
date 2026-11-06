"""Run all adversarial cases and write docs/safety_log.md"""
import json, time
from pathlib import Path
from guardrails import check_input, check_output
ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "eval/adversarial.json").read_text(encoding="utf-8"))
rows, ok = [], 0
def esc(s): return s.replace("|", "/").replace("\n", " ")
for c in D["input_attacks"]:
    v = check_input(c["prompt"]); good = v.blocked and v.category == c["category"]; ok += good
    rows.append(f"| {c['id']} | input | {esc(c['prompt'])} | {c['category']} | {v.category} | {'PASS' if good else 'FAIL'} |")
for c in D["output_attacks"]:
    v = check_output(c["answer"]); good = v.blocked and v.category == c["category"]; ok += good
    rows.append(f"| {c['id']} | output | {esc(c['answer'])} | {c['category']} | {v.category} | {'PASS' if good else 'FAIL'} |")
fp = [q for q in D["benign"] if check_input(q).blocked]
total = len(rows)
md = ["# Safety log (Week 6)", "", f"Run on {time.strftime('%Y-%m-%d %H:%M')}.", "",
      f"- Adversarial cases: {total}, passed: {ok}", f"- Normal questions wrongly blocked: {len(fp)} of {len(D['benign'])}", "",
      "| ID | Stage | Attack | Expected | Got | Result |", "|---|---|---|---|---|---|"] + rows
(ROOT / "docs/safety_log.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"{ok}/{total} passed, false positives: {len(fp)}")
