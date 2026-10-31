# -*- coding: utf-8 -*-
"""比對電路圖網路表（sch.net）與 PCB 焊墊網路，列出差異。
執行："D:\Program Files\KiCad\bin\python.exe" compare_nets.py"""
import os
import re

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def sexpr(text):
    tokens = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t.strip('"'))
    return stack[0][0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


root = sexpr(open(os.path.join(HERE, "sch.net"), encoding="utf-8").read())
sch = {}
for n in find(find(root, "nets")[0], "net"):
    name = find(n, "name")[0][1].lstrip("/")
    nodes = {f'{find(x, "ref")[0][1]}.{find(x, "pin")[0][1]}' for x in find(n, "node")
             if not find(x, "ref")[0][1].startswith("#")}          # PWR_FLAG 不在 PCB 上
    if not name.startswith("unconnected-"):
        sch[name] = nodes

board = pcbnew.LoadBoard(os.path.join(HERE, "EPD24_SuperMini_Adapter.kicad_pcb"))
pcb = {}
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            pcb.setdefault(p.GetNetname(), set()).add(f"{fp.GetReference()}.{p.GetNumber()}")

ok = True
for n in sorted(set(sch) | set(pcb)):
    if sch.get(n, set()) != pcb.get(n, set()):
        ok = False
        print(n, "sch-only:", sorted(sch.get(n, set()) - pcb.get(n, set())),
              "pcb-only:", sorted(pcb.get(n, set()) - sch.get(n, set())))
print(f"{len(sch)} sch nets / {len(pcb)} pcb nets:", "MATCH" if ok else "DIFF")
