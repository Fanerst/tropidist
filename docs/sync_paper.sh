#!/bin/bash
# Regenerates every figure and table of the paper from the records and copies them into a checkout of the paper,
# under the names that ncs.tex reads (figs/ncs/*.pdf, tables/si/*.tex).
# Usage: bash docs/sync_paper.sh PAPER_DIR [PYTHON]
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PAPER=$(cd "$1" && pwd)
PY=${2:-python}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
# the tally of the two-gross scan, which the figures and tables read
(cd "$ROOT/results/bb288_scan" && "$PY" tally_scan.py > /dev/null)
cd "$ROOT"
"$PY" docs/make_ncs_figures.py "$OUT/figs" 1 2 3 4 hook design ablation hyperbolic limit table > /dev/null
"$PY" bench/make_paper_tables.py "$OUT/bench" > /dev/null
# ncs.tex writes these numbers out instead of reading the files, so a changed value has to be changed there by hand
for pair in bench/numbers.tex:numbers figs/si_scan_numbers.tex:scan_numbers figs/si_surgery_numbers.tex:surgery_numbers; do
  if ! cmp -s "$OUT/${pair%%:*}" "$PAPER/tables/si/${pair##*:}.tex"; then
    echo "numbers changed, update them in ncs.tex:"
    diff "$PAPER/tables/si/${pair##*:}.tex" "$OUT/${pair%%:*}" | grep '^[<>]' || true
  fi
done
for f in ncs_fig1 ncs_fig2 ncs_fig3 ncs_fig4 si_hook si_design si_ablation si_hyperbolic si_limit; do
  cp "$OUT/figs/$f.pdf" "$PAPER/figs/ncs/"
done
for pair in si_ibm_fit_table:ibm_fit si_audit_table:audit si_scan_numbers:scan_numbers si_scan_windows_table:scan_windows \
    si_scan_values_table:scan_values si_scan_best_table:scan_best si_cycles_table:cycles si_chips_table:chips \
    si_chips_yield_table:chips_yield si_chips_sim_table:chips_sim si_extended_table:extended \
    si_surgery_adapters_table:surgery_adapters si_surgery_ssip_table:surgery_ssip si_surgery_numbers:surgery_numbers \
    si_ibm_table:ibm si_ibm_spectrum_table:ibm_spectrum si_ibm_sim_table:ibm_sim si_sdbb_table:sdbb; do
  cp "$OUT/figs/${pair%%:*}.tex" "$PAPER/tables/si/${pair##*:}.tex"
done
cp "$OUT/bench/numbers.tex" "$PAPER/tables/si/numbers.tex"
for t in overall_circuit overall_code wjh codes; do
  cp "$OUT/bench/tables/$t.tex" "$PAPER/tables/si/$t.tex"
done
echo "figures and tables copied to $PAPER"
