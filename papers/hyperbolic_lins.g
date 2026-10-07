# Normal subgroups of a triangle group up to an index bound, with GAP's LINS package (the tool
# arXiv:2610.03682 used), written as one JSON object per smooth quotient: the regular permutation
# representation of the quotient on the generators a, b, c (0-based images).
#
# Usage:  gap -q -c 'r:=4;; s:=4;; t:=4;; bound:=1400;; out:="lins_444_1400.jsonl";;' papers/hyperbolic_lins.g
#
# A quotient is smooth (gives a tiling of a closed surface) when a, b, c stay involutions and
# ab, bc, ca keep the orders r, s, t.  `position` is the 1-based position of the normal subgroup in
# the list LINS returns (List of the LinsGraph), all normal subgroups counted, in LINS order.

LoadPackage("LINS");;
F := FreeGroup("a", "b", "c");;
a := F.1;; b := F.2;; c := F.3;;
G := F / [a^2, b^2, c^2, (a*b)^r, (b*c)^s, (c*a)^t];;
gr := LowIndexNormalSubgroupsSearchForAll(G, bound);;
nodes := List(gr);;
if not IsSortedList(List(nodes, x -> Index(x))) and not ForAll([2 .. Length(nodes)], i -> Index(nodes[i-1]) <= Index(nodes[i])) then
    Print("warning: LINS list is not ordered by index; positions follow the LINS order\n");
fi;
Print("normal subgroups up to index ", bound, ": ", Length(nodes), "\n");
stream := OutputTextFile(out, false);;
SetPrintFormattingStatus(stream, false);;
for pos in [1 .. Length(nodes)] do
    node := nodes[pos];
    n := Index(node);
    if n > 1 then
        hom := FactorCosetAction(G, Grp(node));
        img := List(GeneratorsOfGroup(G), g -> Image(hom, g));
        ords := [Order(img[1]), Order(img[2]), Order(img[3]),
                 Order(img[1]*img[2]), Order(img[2]*img[3]), Order(img[3]*img[1])];
        if ords = [2, 2, 2, r, s, t] then
            Q := Group(img);
            orient := Index(Q, Subgroup(Q, [img[1]*img[2], img[2]*img[3]])) = 2;
            if IdGroupsAvailable(n) then id := String(IdGroup(Q)); else id := "none"; fi;
            AppendTo(stream, "{\"position\": ", pos, ", \"order\": ", n,
                     ", \"type\": [", r, ", ", s, ", ", t, "]",
                     ", \"orientable\": ", orient,
                     ", \"id\": \"", id, "\"",
                     ", \"a\": ", List(ListPerm(img[1], n), x -> x - 1),
                     ", \"b\": ", List(ListPerm(img[2], n), x -> x - 1),
                     ", \"c\": ", List(ListPerm(img[3], n), x -> x - 1), "}\n");
        fi;
    fi;
od;
CloseStream(stream);;
Print("written ", out, "\n");
QUIT;
