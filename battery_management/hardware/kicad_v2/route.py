# -*- coding: utf-8 -*-
"""簡易格點自動佈線（雙層 + 過孔），給 build_pcb.py --route 呼叫。

改自 switch_relay_Control/D1mini_Fixture_Shield_HW/kicad/route.py：
0.05mm 格點、A* 搜尋、8 方向走線；每條網路依序佈線，已佈好的銅箔變成後面網路的障礙。
板框除了外框，還有 USB-C 固定腳的 U 形缺口與圓孔，銅箔與板框保持 EDGE 間距。
"""
import heapq
import math

import numpy as np
import pcbnew

import geom as B

G = 0.05
CLEAR = 0.22            # 佈線用間距（DRC 規則 0.15，留餘裕吸收格點誤差）
EDGE = 0.32             # 銅箔到板框（DRC 0.3）
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 30.0
BOTTOM_COST = 1.6
TURN_COST = 6.0
OX, OY = B.OX, B.OY
BW, BH = B.BW, B.BH
NX, NY = int(round(BW / G)) + 1, int(round(BH / G)) + 1

WIDTH = {"VBAT": 0.5, "VSYS": 0.4, "VBUS": 0.4, "GND": 0.4}
DEFAULT_W = 0.25
ORDER = ["VSYS", "VBAT", "VBUS", "PROG", "CHRG", "VBAT_SENSE", "GND"]

_yy, _xx = np.mgrid[0:NY, 0:NX]
GX, GY = _xx * G, _yy * G


def board_mask():
    """True = 板內。"""
    inside = (GX >= 0) & (GX <= BW) & (GY >= 0) & (GY <= BH)
    for cx, cy in B.NOTCHES:
        inside &= ~((GX - cx) ** 2 + (GY - cy) ** 2 <= B.CUT_R ** 2)
        inside &= ~((np.abs(GX - cx) <= B.CUT_R) & (GY <= cy))
    for cx, cy in B.HOLES:
        inside &= ~((GX - cx) ** 2 + (GY - cy) ** 2 <= B.CUT_R ** 2)
    return inside


def dilate(mask, r_mm):
    rr = r_mm / G + 0.5
    r = int(math.ceil(rr))
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > rr * rr or (dx == 0 and dy == 0):
                continue
            sh = np.zeros_like(mask)
            ys = slice(max(dy, 0), NY + min(dy, 0))
            yd = slice(max(-dy, 0), NY + min(-dy, 0))
            xs = slice(max(dx, 0), NX + min(dx, 0))
            xd = slice(max(-dx, 0), NX + min(-dx, 0))
            sh[ys, xs] = mask[yd, xd]
            out |= sh
    return out


OUTSIDE = ~board_mask()
# 板外再往外延伸一圈（邊界格點外也算板外）
OUTSIDE[0, :] |= True
OUTSIDE[-1, :] |= True
OUTSIDE[:, 0] |= True
OUTSIDE[:, -1] |= True


class Grid:
    def __init__(self):
        self.owner = np.zeros((2, NY, NX), dtype=np.int32)
        self.netid = {}

    def nid(self, name):
        if name not in self.netid:
            self.netid[name] = len(self.netid) + 1
        return self.netid[name]

    def paint_rect(self, layer, n, x0, y0, x1, y1):
        e = G * 0.7
        m = (GX >= x0 - e) & (GX <= x1 + e) & (GY >= y0 - e) & (GY <= y1 + e)
        self.owner[layer][m] = n

    def paint_circle(self, layer, n, cx, cy, r):
        r = r + G * 0.7
        m = (GX - cx) ** 2 + (GY - cy) ** 2 <= r * r
        self.owner[layer][m] = n

    def paint_seg(self, layer, n, x0, y0, x1, y1, w):
        r = w / 2 + G * 0.7
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 == 0:
            self.paint_circle(layer, n, x0, y0, w / 2)
            return
        t = np.clip(((GX - x0) * dx + (GY - y0) * dy) / L2, 0, 1)
        px, py = x0 + t * dx, y0 + t * dy
        m = (GX - px) ** 2 + (GY - py) ** 2 <= r * r
        self.owner[layer][m] = n


def pad_geom(p):
    bb = p.GetBoundingBox()
    x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
    x1, y1 = x0 + pcbnew.ToMM(bb.GetWidth()), y0 + pcbnew.ToMM(bb.GetHeight())
    return (0,), "r", (x0, y0, x1, y1)        # 全部是 Top 面 SMD


def run(board, net, pt, mm):
    grid = Grid()
    pads_by_net = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            name = p.GetNetname()
            n = grid.nid(name) if name else 999
            layers, kind, prm = pad_geom(p)
            for L in layers:
                grid.paint_rect(L, n, *prm)
            if name:
                pads_by_net.setdefault(name, []).append((layers, kind, prm))

    tracks, vias = [], []

    def add_track(name, layer, a, b, w):
        tracks.append((name, layer, a[0], a[1], b[0], b[1], w))
        grid.paint_seg(layer, grid.nid(name), a[0], a[1], b[0], b[1], w)

    def add_via(name, x, y):
        vias.append((name, x, y))
        for L in (0, 1):
            grid.paint_circle(L, grid.nid(name), x, y, VIA_D / 2)

    edge_cache = {}

    def edge(r):
        if r not in edge_cache:
            edge_cache[r] = dilate(OUTSIDE, r)
        return edge_cache[r]

    def pin_cells(pin):
        layers, kind, (x0, y0, x1, y1) = pin
        cells = []
        for iy in range(int(math.ceil(y0 / G)), int(math.floor(y1 / G)) + 1):
            for ix in range(int(math.ceil(x0 / G)), int(math.floor(x1 / G)) + 1):
                for L in layers:
                    cells.append((L, ix, iy))
        return cells

    def astar(src, dst, blocked, via_ok):
        tx = [c[1] for c in dst]
        ty = [c[2] for c in dst]
        cx, cy = sum(tx) / len(tx), sum(ty) / len(ty)

        def hfun(ix, iy):
            return math.hypot(ix - cx, iy - cy) * 0.9

        steps = [(1, 0, 1.0), (1, 1, 1.414), (0, 1, 1.0), (-1, 1, 1.414),
                 (-1, 0, 1.0), (-1, -1, 1.414), (0, -1, 1.0), (1, -1, 1.414)]
        dist, prev, pq = {}, {}, []
        for c in src:
            L, ix, iy = c
            if 0 <= ix < NX and 0 <= iy < NY:
                s0 = (L, ix, iy, 8)
                dist[s0] = 0.0
                heapq.heappush(pq, (hfun(ix, iy), 0.0, s0))
        while pq:
            f, d, st = heapq.heappop(pq)
            if d > dist.get(st, 1e18):
                continue
            L, ix, iy, dr = st
            if (L, ix, iy) in dst:
                path = [st]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return [(q[0], q[1], q[2]) for q in path[::-1]]
            k = BOTTOM_COST if L == 1 else 1.0
            for nd_i, (dx, dy, sc) in enumerate(steps):
                if dr != 8:
                    turn = min((nd_i - dr) % 8, (dr - nd_i) % 8)
                    if turn > 2:
                        continue
                else:
                    turn = 0
                nx, ny = ix + dx, iy + dy
                if not (0 <= nx < NX and 0 <= ny < NY):
                    continue
                cell = (L, nx, ny)
                if blocked[L][ny, nx] and cell not in dst:
                    continue
                if dx and dy and (blocked[L][iy, nx] or blocked[L][ny, ix]) and cell not in dst:
                    continue
                ns = (L, nx, ny, nd_i)
                nd = d + sc * k + turn * TURN_COST
                if nd < dist.get(ns, 1e18):
                    dist[ns] = nd
                    prev[ns] = st
                    heapq.heappush(pq, (nd + hfun(nx, ny), nd, ns))
            if via_ok[iy, ix]:
                cell = (1 - L, ix, iy)
                if not blocked[1 - L][iy, ix] or cell in dst:
                    ns = (1 - L, ix, iy, 8)
                    nd = d + VIA_COST
                    if nd < dist.get(ns, 1e18):
                        dist[ns] = nd
                        prev[ns] = st
                        heapq.heappush(pq, (nd + hfun(ix, iy), nd, ns))
        return None

    def emit(name, path, w):
        seg_start = path[0]
        prev_c = path[0]
        prev_dir = None
        for c in path[1:]:
            if c[0] != prev_c[0]:
                if seg_start != prev_c:
                    add_track(name, prev_c[0], (seg_start[1] * G, seg_start[2] * G), (prev_c[1] * G, prev_c[2] * G), w)
                add_via(name, prev_c[1] * G, prev_c[2] * G)
                seg_start, prev_dir = c, None
                prev_c = c
                continue
            d = (c[1] - prev_c[1], c[2] - prev_c[2])
            if prev_dir is not None and d != prev_dir:
                add_track(name, prev_c[0], (seg_start[1] * G, seg_start[2] * G), (prev_c[1] * G, prev_c[2] * G), w)
                seg_start = prev_c
            prev_dir = d
            prev_c = c
        if seg_start != prev_c:
            add_track(name, prev_c[0], (seg_start[1] * G, seg_start[2] * G), (prev_c[1] * G, prev_c[2] * G), w)

    def route_net(name):
        n = grid.nid(name)
        w = WIDTH.get(name, DEFAULT_W)
        h = w / 2
        other = [(grid.owner[L] != 0) & (grid.owner[L] != n) for L in (0, 1)]
        blocked = [dilate(other[L], CLEAR + h) | edge(EDGE + h) for L in (0, 1)]
        via_ok = ~(dilate(other[0] | other[1], CLEAR + VIA_D / 2) | edge(EDGE + VIA_D / 2))
        pins = pads_by_net[name]
        tree = set(pin_cells(pins[0]))
        for pin in pins[1:]:
            target = set(pin_cells(pin))
            if target & tree:
                continue
            path = astar(tree, target, blocked, via_ok)
            if path is None:
                raise RuntimeError(f"route failed: {name} -> {pin[2]}")
            emit(name, path, w)
            tree.update(path)
            tree |= target

    for name in ORDER:
        route_net(name)
        print("routed", name)

    for name, L, x0, y0, x1, y1, w in tracks:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(x0, y0))
        t.SetEnd(pt(x1, y1))
        t.SetWidth(mm(w))
        t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu)
        t.SetNet(net(name))
        board.Add(t)
    for name, x, y in vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(net(name))
        board.Add(v)
    print(f"tracks {len(tracks)}, vias {len(vias)}")

    # 兩面鋪 GND（填充時 KiCad 會自動避開板框與缺口）
    for layer in (pcbnew.B_Cu, pcbnew.F_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net("GND"))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0, 0), (BW, 0), (BW, BH), (0, BH)):
            ol.Append(mm(OX + x), mm(OY + y))
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.25))
        z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    print("zones filled")
