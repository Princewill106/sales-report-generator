"""Automated Sales Report Generator."""
import argparse
import csv
import html
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import llm


def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        r["d"] = date.fromisoformat(r["date"])
        r["rev"] = int(r["qty"]) * float(r["unit_price"])
    return rows


def kpis(rows):
    rev = sum(r["rev"] for r in rows)
    orders = len({r["order_id"] for r in rows})
    return {"revenue": rev, "orders": orders, "aov": rev / orders if orders else 0}


def by(rows, key):
    out = defaultdict(float)
    for r in rows:
        out[r[key]] += r["rev"]
    return out


def pct(a, b):
    return (a - b) / b * 100 if b else 0.0


def build(rows):
    end = max(r["d"] for r in rows)
    start = end - timedelta(days=6)
    this = [r for r in rows if start <= r["d"] <= end]
    prev = [r for r in rows if start - timedelta(days=7) <= r["d"] < start]
    k1, k0 = kpis(this), kpis(prev)
    p1, p0 = by(this, "product"), by(prev, "product")
    movers = sorted(((p, p1.get(p, 0) - p0.get(p, 0)) for p in set(p1) | set(p0)),
                    key=lambda x: -x[1])
    branches = sorted(by(this, "branch").items(), key=lambda x: -x[1])
    notes = [
        f"Revenue {'rose' if k1['revenue'] >= k0['revenue'] else 'fell'} "
        f"{abs(pct(k1['revenue'], k0['revenue'])):.1f}% to NGN {k1['revenue']:,.0f}.",
        f"Biggest gain: {movers[0][0]} (+NGN {movers[0][1]:,.0f}).",
        f"Biggest drop: {movers[-1][0]} (NGN {movers[-1][1]:,.0f}).",
        f"Top branch: {branches[0][0]} with NGN {branches[0][1]:,.0f}.",
    ]
    return {"start": start, "end": end, "k1": k1, "k0": k0, "movers": movers,
            "branches": branches, "notes": notes}


def to_markdown(r, commentary):
    k1, k0 = r["k1"], r["k0"]
    rows = [("Revenue", k1["revenue"], k0["revenue"]), ("Orders", k1["orders"], k0["orders"]),
            ("Avg order value", k1["aov"], k0["aov"])]
    lines = [f"# Weekly sales report: {r['start']} to {r['end']}", "",
             "| Metric | This week | Last week | Change |", "|---|---:|---:|---:|"]
    lines += [f"| {n} | {a:,.0f} | {b:,.0f} | {pct(a, b):+.1f}% |" for n, a, b in rows]
    lines += ["", "## What changed", ""] + [f"- {n}" for n in commentary]
    lines += ["", "## Branches", ""] + [f"- {b}: NGN {v:,.0f}" for b, v in r["branches"]]
    return "\n".join(lines)


def to_html(r, commentary):
    top = r["branches"][0][1] or 1
    bars = "".join(f"<div style='margin:4px 0'>{html.escape(b)}<div style='background:#6d28d9;height:14px;"
                   f"width:{v / top * 100:.0f}%'></div></div>" for b, v in r["branches"])
    items = "".join(f"<li>{html.escape(n)}</li>" for n in commentary)
    return (f"<html><body style='font-family:sans-serif;max-width:640px;margin:auto'>"
            f"<h1>Weekly sales {r['start']} – {r['end']}</h1>"
            f"<h2>NGN {r['k1']['revenue']:,.0f} <small>({pct(r['k1']['revenue'], r['k0']['revenue']):+.1f}%)</small></h2>"
            f"<ul>{items}</ul><h3>Revenue by branch</h3>{bars}</body></html>")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="sample_sales.csv")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    r = build(load(a.input))
    ai = llm.complete("Write 3 short bullet points of commentary for a managing director "
                      "based on these facts:\n" + "\n".join(r["notes"]))
    commentary = [l.strip("-• ") for l in ai.splitlines() if l.strip()] if ai else r["notes"]
    md = to_markdown(r, commentary)
    Path("output").mkdir(exist_ok=True)
    Path("output/weekly_report.md").write_text(md)
    Path("output/weekly_report.html").write_text(to_html(r, commentary))
    print(md)
    print("\nSaved output/weekly_report.md and output/weekly_report.html")


if __name__ == "__main__":
    main()
