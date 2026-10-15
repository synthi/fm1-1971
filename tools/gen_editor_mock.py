#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Regenerate web/editor.html's mock device tables from build/host/desc.json (the firmware's own tables).

The mock's ENG/GP[ENG]/ENGINE_ORDER must equal what tests/descdump.c dumps from the firmware;
tests/run_tests.sh (web test) fails otherwise. Run after any engine/page change:

    build/host/descdump > build/host/desc.json && tools/gen_editor_mock.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "web" / "editor.html"
DESC = ROOT / "build" / "host" / "desc.json"

F = {0: "F.INT", 1: "F.PCT", 2: "F.BIPCT", 3: "F.TIME", 4: "F.LFOHZ", 5: "F.CUTOFF",
     6: "F.DB", 7: "F.SEMI", 8: "F.ENUM", 9: "F.BPM", 10: "F.NOTE", 11: "F.ONOFF",
     12: "F.OCT", 13: "F.STEPS"}


def js_names(names):
    return "[" + ", ".join(json.dumps(n) for n in names) + "]"


def js_ints(values):
    return "[" + ", ".join(str(int(v)) for v in values) + "]"


def edit_row(d):
    unit = d.get("unit") or ""
    fmt = F.get(d["fmt"], str(d["fmt"]))
    names = d.get("names")
    args = [json.dumps(d["label"]), fmt, str(d["min"]), str(d["max"]), str(d["def"])]
    if names:
        args.append(js_names(names))
        if unit:
            args.append(json.dumps(unit))
    elif unit:
        args.append("null")
        args.append(json.dumps(unit))
    return "D(" + ", ".join(args) + ")"


def engine_entry(i, e):
    if e["name"] == "-":
        return ('    {name:"-",titles:["-","-"],edit:Array(8).fill(NONE),presets:[]}'
                f'   /* {i}: retired; stored ID reserved */')
    rows = ",\n            ".join(edit_row(d) for d in e["edit"])
    presets = []
    for p in e["presets"]:
        presets.append("P({}, {}, {}, {})".format(
            json.dumps(p["name"]), js_ints(p["e"]), js_ints(p["env"]), int(p["mono"])))
    preset_rows = ", ".join(presets)
    return (f'    {{name:{json.dumps(e["name"])},titles:{js_names(e["titles"])},edit:[\n'
            f"            {rows}],presets:[\n"
            f"            {preset_rows}]}}   /* {i} */")


def main():
    if not DESC.exists():
        sys.exit(f"missing {DESC} (build/host/descdump > build/host/desc.json)")
    fw = json.loads(DESC.read_text())
    html = HTML.read_text()

    # 1. the ENG array inside makeMockDevice()
    start = html.index("  const ENG = [")
    end = html.index("\n  ];", start) + len("\n  ];")
    entries = ",\n".join(engine_entry(i, e) for i, e in enumerate(fw["ENG"]))
    html = html[:start] + "  const ENG = [\n" + entries + "\n  ];" + html[end:]

    # 2. the ENG parameter row of GP (the engine-name menu the panel shows)
    gname = fw["GP"][fw["G_ENGSEL"]]["names"]
    gp_new = 'E("ENG", ' + js_names(gname) + ", 0)"
    html, n = re.subn(r'E\("ENG", \[[^\]]*\], 0\)', gp_new.replace("\\", "\\\\"), html, count=1)
    if n != 1:
        sys.exit("GP ENG row not found")

    # 3. ENGINE_ORDER (the rank list engineOrder() sorts the names by)
    rank = list(fw["ORDER"])
    rank.insert(1, "ANALOG")           # kept in the list; never in fw names any more (1971)
    rank.insert(3, "DIGITAL")
    html, n = re.subn(r'const ENGINE_ORDER = \[[^\]]*\];',
                      "const ENGINE_ORDER = " + js_names(rank) + ";", html, count=1)
    if n != 1:
        sys.exit("ENGINE_ORDER not found")
    HTML.write_text(html)
    print(f"editor.html mock regenerated from {DESC.name}: {len(fw['ENG'])} engines, "
          f"ORDER {fw['ORDER']}")


if __name__ == "__main__":
    main()
