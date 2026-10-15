"""Export the CSS code instances of arXiv:2603.22532 (Webster, Jacob, Higgott) from their codeDistance
package (github.com/m-webster/codeDistancePYPI, MIT licence) as plain check matrices.

The package builds its codes with its own functions (bivariate bicycle, lifted product, quantum Tanner,
hyperbolic surface and colour codes from RG-3-8.txt); this script calls exactly those, in the order and
with the filter of their examples/runTest.py (codes with k > 0), so that every instance is the one their
tables report.  Their distance module imports gurobipy and OR-Tools at load time although building codes
needs neither; both are replaced by empty modules here, nothing is installed.  Needs numpy, scipy and numba.

usage: python papers/codedistance_export.py <codeDistancePYPI checkout> <out.json>
"""
import json
import os
import sys
import types


def stub(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


def main():
    repo, out_path = (os.path.abspath(x) for x in sys.argv[1:3])
    pywraplp = stub("ortools.linear_solver.pywraplp")
    linear_solver = stub("ortools.linear_solver", pywraplp=pywraplp)
    stub("ortools", linear_solver=linear_solver)
    stub("gurobipy", GRB=None)
    sys.path[:0] = [repo, os.path.join(repo, "examples")]
    os.chdir(os.path.join(repo, "examples"))       # their loaders read paths relative to examples/
    import numpy as np
    import codedistance as cd
    import bivariate_bicycle
    import lifted_product
    import QT_codes

    def rows(m):
        m = np.asarray(m, dtype=np.int64) % 2
        return [[int(j) for j in np.flatnonzero(r)] for r in m]

    out = []

    def add(family, code):
        if code["k"] <= 0:                          # runTest.py: ignoreTrivialCodes = 1
            return
        out.append(dict(family=family, index=sum(1 for c in out if c["family"] == family), name=code["name"],
                        n=int(code["n"]), k=int(code["k"]), d_listed=int(code["d"]),
                        hx=rows(code["SX"]), hz=rows(code["SZ"])))

    for code in bivariate_bicycle.BBCodeList():
        add("bb", code)
    for code in lifted_product.LPCodeList():
        add("lp", code)
    for code in QT_codes.QTCodeList():
        add("qt", code)
    for family, maker in (("hsc", "surface"), ("hcc", "colour")):
        for _, cplx in cd.importRGList("hyperbolic_codes/RG-3-8.txt"):
            if maker == "surface":
                hz, hx = cd.complex2SurfaceCode(cplx)   # as runTest.py: Hz, Hx = complex2SurfaceCode(...)
            else:
                hx, hz = cd.complex2ColourCode(cplx)
            add(family, cd.CSS2Dict(hx, hz))
    with open(out_path, "w") as f:
        json.dump(dict(source="github.com/m-webster/codeDistancePYPI", codes=out), f)
    counts = {}
    for c in out:
        counts[c["family"]] = counts.get(c["family"], 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
