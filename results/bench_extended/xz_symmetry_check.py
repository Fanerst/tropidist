"""Does a code have a qubit permutation that exchanges its X and Z checks?  Then its X and Z distances are equal, so a run in one basis gives the code distance.
Graph isomorphism of the Tanner graph with the check colors swapped (networkx VF2), one code at a time with a time limit; bb codes as a control."""
import json
import signal
import sys

import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher, categorical_node_match

codes = json.load(open("papers/downloads/codedistance_codes.json"))["codes"]
want = [("bb", 10), ("qt", 7), ("qt", 8), ("qt", 9), ("qt", 10), ("bb", 6)]


class Timeout(Exception):
    pass


def alarm(*_):
    raise Timeout()


signal.signal(signal.SIGALRM, alarm)
for fam, idx in want:
    c = next(x for x in codes if x["family"] == fam and x["index"] == idx)
    hx, hz = c["hx"], c["hz"]
    G1, G2 = nx.Graph(), nx.Graph()
    for q in range(c["n"]):
        G1.add_node(("q", q), t="q")
        G2.add_node(("q", q), t="q")
    for name, H, a, b in (("x", hx, "A", "B"), ("z", hz, "B", "A")):
        for i, row in enumerate(H):
            G1.add_node((name, i), t=a)
            G2.add_node((name, i), t=b)
            for q in row:
                G1.add_edge((name, i), ("q", q))
                G2.add_edge((name, i), ("q", q))
    deg = lambda H: sorted({len(r) for r in H})
    print(c["name"], "rows", len(hx), len(hz), "row weights", deg(hx), deg(hz), flush=True, end=" ")
    signal.alarm(int(sys.argv[1]) if len(sys.argv) > 1 else 150)
    try:
        ok = GraphMatcher(G1, G2, node_match=categorical_node_match("t", None)).is_isomorphic()
        print("X and Z exchangeable:", ok, flush=True)
    except Timeout:
        print("no answer within the limit", flush=True)
    finally:
        signal.alarm(0)
