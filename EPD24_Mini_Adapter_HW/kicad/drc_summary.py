# -*- coding: utf-8 -*-
"""跑 kicad-cli DRC（英文訊息）並印出摘要。執行：python drc_summary.py"""
import collections
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"D:\Program Files\KiCad\bin\kicad-cli.exe"
env = dict(os.environ, LANG="en_US", LC_ALL="en_US.UTF-8", KICAD_LANG="en")
subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", os.path.join(HERE, "drc.json"),
                os.path.join(HERE, "EPD24_Mini_Adapter.kicad_pcb")], env=env, check=True, capture_output=True)
d = json.load(open(os.path.join(HERE, "drc.json"), encoding="utf-8"))
print("violations:", dict(collections.Counter((v["type"], v["severity"]) for v in d["violations"])))
print("unconnected:", len(d["unconnected_items"]))
for v in d["violations"]:
    if v["severity"] == "error":
        print(" ", v["type"], "|", v["description"], "|", " / ".join(i["description"] for i in v["items"]),
              "|", [(round(i["pos"]["x"] - 100, 2), round(i["pos"]["y"] - 100, 2)) for i in v["items"]])
for u in d["unconnected_items"]:
    print("  unconnected:", " / ".join(i["description"] for i in u["items"]),
          [(round(i["pos"]["x"] - 100, 2), round(i["pos"]["y"] - 100, 2)) for i in u["items"]])
