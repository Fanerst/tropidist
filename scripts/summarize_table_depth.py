"""Tables of results/table_depth (scripts/table_depth_probe.py runs): every instance variant with lookup tables of
the depth before 7ef27aa (budget 1 GiB), as deep as 8 GiB allow up front (7ef27aa), and with the depth rule of
bench/adapters/ours_pipeline.py (up front within EAGER_TABLE_BYTES, deepened after a paired trial), and the
trials of the rule.

usage: python scripts/summarize_table_depth.py [results/table_depth]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(path):
    if not path.exists():
        return ""
    r = json.loads(path.read_text())
    if r["status"] == "exact":
        return "%.1f s" % r["seconds"]
    return "%s %s..%s" % (r["status"], r["lower"], "" if r["upper"] is None else r["upper"])


def main(folder):
    folder = Path(folder)
    runs = sorted({p.name.split("__b1__")[0] + "__" + p.name.rsplit("__", 1)[1][:-5]
                   for p in folder.glob("*__b1__*.json")})
    out = ["| instance variant | threads | 1 GiB (before 7ef27aa) | 8 GiB up front (7ef27aa) | rule |",
           "|---|---:|---:|---:|---:|"]
    trials = []
    for run in runs:
        name, t = run.rsplit("__", 1)
        rule = folder / ("%s__final__%s.json" % (name, t))        # the rule as committed
        out.append("| %s | %s | %s | %s | %s |" % (name.replace("__", " "), t[1:], cell(folder / ("%s__b1__%s.json" % (name, t))),
                                                cell(folder / ("%s__b8__%s.json" % (name, t))), cell(rule)))
        if rule.exists():
            for stage, ts in json.loads(rule.read_text()).get("deepen", {}).items():
                trials += [(name.replace("__", " "), stage, x) for x in ts]
    out += ["", "Trials of the rule (level K with depth k - 1 took level_seconds; build of depth k; the same sample of "
            "anchors with both):", "",
            "| instance variant | stage | K | k | level | build | anchors | shallow | deep | decision |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name, stage, x in trials:
        if "shallow" in x:                    # time-boxed trial: [status, seconds, nodes at the compared depth]
            sh = "%.2f s, %s nodes%s" % (x["shallow"][1], "{:,}".format(x["shallow"][2]),
                                          " (limit)" if x["shallow"][0] == "timeout" else "")
            dp = "%.2f s, %s nodes%s" % (x["deep"][1], "{:,}".format(x["deep"][2]),
                                          " (limit)" if x["deep"][0] == "timeout" else "")
        else:                                 # the first version: the shallow run had no time limit
            sh = "%.2f s" % x.get("shallow_seconds", 0)
            dp = "%.2f s%s" % (x.get("deep_seconds", 0), " (limit)" if x.get("deep_status") == "timeout" else "")
        out.append("| %s | %s | %d | %d | %.1f s | %.1f s | %d | %s | %s | %s |" % (
            name, stage, x["K"], x["k"], x["level_seconds"], x.get("build_seconds", 0), x.get("sample_anchors", 0),
            sh, dp, x["decision"]))
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "results" / "table_depth")
