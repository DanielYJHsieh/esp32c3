# -*- coding: utf-8 -*-
"""簡易格點自動佈線（雙層 + 過孔），給 build_pcb.py --route 呼叫。

改自 D1mini_Fixture_Shield_HW/kicad/route.py：格點改 0.05mm、間距 0.15mm，才走得進 0.5mm 腳距的 FPC 焊墊。
做法：A* 搜尋、8 方向走線；每條網路依序佈線，已佈好的銅箔變成後面網路的障礙。
障礙 = 其他網路的銅箔往外擴「安全間距 + 本網路線寬/2」；板邊內縮 0.3mm（JLCPCB）。
"""
import heapq
import math

import numpy as np
import pcbnew

G = 0.05                # 格點 mm
CLEAR = 0.15            # 佈線用間距 mm：DRC 規則 0.127；焊墊已外擴 0.035 吸收格點誤差
EDGE = 0.3              # 銅箔到板框 mm
VIA_D, VIA_DRILL = 0.5, 0.3
VIA_COST = 12.0
BOTTOM_COST = 1.6       # 底層每格成本加權：盡量走頂層，底層留給 GND 鋪銅
TURN_COST = 3.0         # 每轉 45° 的成本：讓走線少轉彎、比較直
OX, OY = 100.0, 100.0
BW, BH = 18.0, 19.9
NX, NY = int(round(BW / G)) + 1, int(round(BH / G)) + 1

# 佈線順序與線寬（mm）：升壓迴路先走、走粗；FPC 焊墊只有 0.3mm 寬，訊號線 0.15mm
WIDTH = {"SW": 0.3, "RESE": 0.3, "3V3": 0.25, "GND": 0.3, "NEG": 0.3, "PREVGH": 0.25, "PREVGL": 0.25}
DEFAULT_W = 0.15
PRE_TRACKS = []   # (網路, (x0, y0), (x1, y1))：build_pcb.py 設定，佈線前先拉的頂層短線
ORDER = ["VCOM", "PREVGL", "SDI", "VSH", "VDD", "VSL", "PREVGH", "SW", "RESE", "GDR", "NEG", "3V3", "VGH",
         "VGL", "VPP", "BUSY", "RES", "DC", "CS", "SCLK", "GND"]   # build_pcb.py 自動重試後找到的可行順序
# GND 最後走：訊號線走完後盡量用線把 GND 焊墊接起來（J2 的 GND 焊點會被兩側訊號線圍住），
# 走不到的再靠接地過孔（build_pcb.py STITCH）和兩面鋪銅；DRC 確認沒有未連接


def to_mm(v):
    return pcbnew.ToMM(v)


class Grid:
    def __init__(self):
        # owner[layer][iy][ix] = 網路編號；0 = 空
        self.owner = np.zeros((2, NY, NX), dtype=np.int32)
        self.netid = {}
        yy, xx = np.mgrid[0:NY, 0:NX]
        self.X = xx * G
        self.Y = yy * G

    def nid(self, name):
        if name not in self.netid:
            self.netid[name] = len(self.netid) + 1
        return self.netid[name]

    # --- 畫銅箔進 owner
    def paint_rect(self, layer, n, x0, y0, x1, y1):
        e = G * 0.7
        m = (self.X >= x0 - e) & (self.X <= x1 + e) & (self.Y >= y0 - e) & (self.Y <= y1 + e)
        self.owner[layer][m] = n

    def paint_circle(self, layer, n, cx, cy, r):
        r = r + G * 0.7
        m = (self.X - cx) ** 2 + (self.Y - cy) ** 2 <= r * r
        self.owner[layer][m] = n

    def paint_seg(self, layer, n, x0, y0, x1, y1, w):
        r = w / 2 + G * 0.7
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 == 0:
            self.paint_circle(layer, n, x0, y0, r)
            return
        t = ((self.X - x0) * dx + (self.Y - y0) * dy) / L2
        t = np.clip(t, 0, 1)
        px, py = x0 + t * dx, y0 + t * dy
        m = (self.X - px) ** 2 + (self.Y - py) ** 2 <= r * r
        self.owner[layer][m] = n


def dilate(mask, r_mm):
    r = int(math.ceil(r_mm / G + 0.5))
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > (r_mm / G + 0.5) ** 2:
                continue
            if dx == 0 and dy == 0:
                continue
            sh = np.zeros_like(mask)
            ys = slice(max(dy, 0), NY + min(dy, 0))
            yd = slice(max(-dy, 0), NY + min(-dy, 0))
            xs = slice(max(dx, 0), NX + min(dx, 0))
            xd = slice(max(-dx, 0), NX + min(-dx, 0))
            sh[ys, xs] = mask[yd, xd]
            out |= sh
    return out


def edge_band(r_mm):
    g = Grid.__new__(Grid)
    yy, xx = np.mgrid[0:NY, 0:NX]
    X, Y = xx * G, yy * G
    return (X < r_mm) | (X > BW - r_mm) | (Y < r_mm) | (Y > BH - r_mm)


def pad_geom(p):
    """回傳 (layers, kind, params)，座標相對板子左上角 (mm)。"""
    bb = p.GetBoundingBox()
    x0, y0 = to_mm(bb.GetX()) - OX, to_mm(bb.GetY()) - OY
    x1, y1 = x0 + to_mm(bb.GetWidth()), y0 + to_mm(bb.GetHeight())
    tht = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
    layers = (0, 1) if tht else (0,)
    try:
        shape = p.GetShape(pcbnew.F_Cu)
    except TypeError:
        shape = p.GetShape()
    if shape == pcbnew.PAD_SHAPE_CIRCLE:
        return layers, "c", ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2)
    return layers, "r", (x0, y0, x1, y1)


def debug_png(name, blocked, via_ok, src, dst):
    """把兩層的可走區域畫成 PNG（左頂層、右底層）：黑 = 不可走，白 = 可走，淡藍 = 不能打過孔，綠 = 起點樹，紅 = 目標。"""
    import struct
    import zlib
    S = 3
    W, H = (NX * 2 + 10) * S, NY * S
    img = np.full((H, W, 3), 255, np.uint8)
    for L in (0, 1):
        off = L * (NX + 10)
        b = np.repeat(np.repeat(blocked[L], S, 0), S, 1)
        sub = img[:, off * S:(off + NX) * S]
        sub[b] = (40, 40, 40)
        if L == 0:
            v = np.repeat(np.repeat(~via_ok, S, 0), S, 1)
            sub[v & ~b] = (200, 200, 255)
    for cells, col in ((src, (0, 200, 0)), (dst, (230, 0, 0))):
        for L, ix, iy in cells:
            off = L * (NX + 10)
            img[iy * S:(iy + 1) * S, (off + ix) * S:(off + ix + 1) * S] = col
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(H))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    open(f"debug_{name}.png", "wb").write(png)


class RouteFailed(RuntimeError):
    def __init__(self, name):
        super().__init__(f"route failed: {name}")
        self.net = name


def run(board, net, pt, mm, stitches=(), order=None):
    """stitches = [(網路, (焊墊 x, y), (過孔 x, y))]：先放好的過孔，焊墊用短線接過去。"""
    grid = Grid()
    pads_by_net = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            name = p.GetNetname()
            n = grid.nid(name) if name else 999
            layers, kind, prm = pad_geom(p)
            for L in layers:
                if kind == "c":
                    grid.paint_circle(L, n, *prm)
                else:
                    grid.paint_rect(L, n, *prm)
            if name:
                pads_by_net.setdefault(name, []).append((layers, kind, prm))

    tracks = []   # (net, layer, x0, y0, x1, y1, w)
    vias = []     # (net, x, y)

    def add_track(name, layer, a, b, w):
        tracks.append((name, layer, a[0], a[1], b[0], b[1], w))
        grid.paint_seg(layer, grid.nid(name), a[0], a[1], b[0], b[1], w)

    def add_via(name, x, y):
        for vn, vx, vy in vias:              # 附近已有同網路過孔就共用（避免兩顆鑽孔疊在一起），兩層各補一段線接過去
            if vn == name and math.hypot(x - vx, y - vy) < VIA_D + 0.05:
                if (vx, vy) != (x, y):
                    for L in (0, 1):
                        add_track(name, L, (x, y), (vx, vy), DEFAULT_W)
                return
        vias.append((name, x, y))
        for L in (0, 1):
            grid.paint_circle(L, grid.nid(name), x, y, VIA_D / 2)

    # ---- 先拉的短線：同網路相鄰焊墊直接連（例如 FPC pin 15/16 都是 3V3），免得佈線斜接造成銅頸過窄
    for name, a, b in PRE_TRACKS:
        add_track(name, 0, a, b, 0.3)

    # ---- 先放的接地過孔：被訊號線圍住的小電容 GND 腳直接打到底層鋪銅
    for name, pad_xy, via_xy in stitches:
        add_track(name, 0, pad_xy, via_xy, 0.25)
        add_via(name, *via_xy)

    edge_cache = {}

    def edge(r):
        if r not in edge_cache:
            edge_cache[r] = edge_band(r)
        return edge_cache[r]

    def route_net(name):
        n = grid.nid(name)
        w = WIDTH.get(name, DEFAULT_W)
        h = w / 2
        other = [(grid.owner[L] != 0) & (grid.owner[L] != n) for L in (0, 1)]
        blocked = [dilate(other[L], CLEAR + h) | edge(EDGE + h) for L in (0, 1)]
        via_ok = ~(dilate(other[0] | other[1], CLEAR + VIA_D / 2) | edge(EDGE + VIA_D / 2))

        pins = pads_by_net[name]

        def pin_cells(pin):
            layers, kind, prm = pin
            cells = []
            if kind == "c":
                cx, cy, r = prm
                x0, y0, x1, y1 = cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7
            else:
                x0, y0, x1, y1 = prm
            for iy in range(int(math.ceil(y0 / G)), int(math.floor(y1 / G)) + 1):
                for ix in range(int(math.ceil(x0 / G)), int(math.floor(x1 / G)) + 1):
                    for L in layers:
                        cells.append((L, ix, iy))
            return cells

        def inside(pin, xy):
            layers, kind, prm = pin
            if kind == "c":
                return math.hypot(xy[0] - prm[0], xy[1] - prm[1]) <= prm[2]
            return prm[0] <= xy[0] <= prm[2] and prm[1] <= xy[1] <= prm[3]

        def with_partners(pin):              # 焊墊加上 PRE_TRACKS 已經直接連好的焊墊
            cells = set(pin_cells(pin))
            for nm, a, b in PRE_TRACKS:
                if nm != name:
                    continue
                for p, q in ((a, b), (b, a)):
                    if inside(pin, p):
                        for other_pin in pins:
                            if inside(other_pin, q):
                                cells |= set(pin_cells(other_pin))
            return cells

        tree = with_partners(pins[0])

        for pin in pins[1:]:
            target = with_partners(pin)
            if target & tree:
                continue
            path = astar(tree, target, blocked, via_ok)
            if path is None:
                if name == "GND":          # GND 走不到的腳交給兩面鋪銅，最後看 DRC 有沒有未連接
                    print("  GND pad left to zone:", pin[2])
                    continue
                debug_png(name, blocked, via_ok, tree, target)
                raise RouteFailed(name)
            emit(name, path, w)
            # 路徑端點只碰到焊墊邊緣時，補一段線拉到焊墊中心，避免斜角碰邊造成連接過窄
            for L, ix, iy in (path[0], path[-1]):
                ex, ey = ix * G, iy * G
                for layers, kind, prm in pins:
                    if kind != "r" or L not in layers:
                        continue
                    x0, y0, x1, y1 = prm
                    if x0 - G <= ex <= x1 + G and y0 - G <= ey <= y1 + G:
                        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                        if abs(cx - ex) > 1e-6 or abs(cy - ey) > 1e-6:
                            add_track(name, L, (ex, ey), (cx, cy), min(w, x1 - x0, y1 - y0))
                        break
            for c in path:
                tree.add(c)
            tree |= target

    def astar(src, dst, blocked, via_ok):
        tx = [c[1] for c in dst]
        ty = [c[2] for c in dst]
        cx, cy = sum(tx) / len(tx), sum(ty) / len(ty)

        def hfun(ix, iy):
            return math.hypot(ix - cx, iy - cy) * 0.9

        # 狀態 = (層, x, y, 方向)；方向 8 = 尚未決定（起點或剛換層）
        steps = [(1, 0, 1.0), (1, 1, 1.414), (0, 1, 1.0), (-1, 1, 1.414),
                 (-1, 0, 1.0), (-1, -1, 1.414), (0, -1, 1.0), (1, -1, 1.414)]
        dist = {}
        prev = {}
        pq = []
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
                    if turn > 2:          # 不允許大於 90° 的急轉
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
            # 換層（過孔）
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
        # 把格點路徑壓成線段；換層處放過孔
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

    for name in (order or ORDER):
        route_net(name)
        print("routed", name)

    # ---- GND 縫合過孔：空位每 1.5mm 打一顆，把兩面鋪銅的碎片接在一起
    gid = grid.nid("GND")
    other_any = ((grid.owner[0] != 0) & (grid.owner[0] != gid)) | ((grid.owner[1] != 0) & (grid.owner[1] != gid))
    free_via = ~(dilate(other_any, CLEAR + 0.1 + VIA_D / 2) | edge_band(EDGE + VIA_D / 2 + 0.1))
    used = [(x, y) for _, x, y in vias]
    for fp in board.GetFootprints():                 # 排針孔也要避開（鑽孔間距）
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                c = p.GetPosition()
                used.append((to_mm(c.x) - OX, to_mm(c.y) - OY))
    n_stitch = 0
    step = 1.5
    y = 0.8
    while y < BH - 0.8:
        x = 0.8
        while x < BW - 0.8:
            ix, iy = int(round(x / G)), int(round(y / G))
            if free_via[iy, ix] and all(math.hypot(x - vx, y - vy) >= 1.2 for vx, vy in used):
                add_via("GND", x, y)
                used.append((x, y))
                n_stitch += 1
            x += step
        y += step
    print("GND stitching vias:", n_stitch)

    # ---- 寫回 KiCad
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

    # ---- 兩面鋪 GND
    for layer in (pcbnew.B_Cu, pcbnew.F_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net("GND"))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0, 0), (BW, 0), (BW, BH), (0, BH)):
            ol.Append(mm(OX + x), mm(OY + y))
        z.SetLocalClearance(mm(0.2))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)   # 0402 用散熱連接，回焊比較不會立碑
        z.SetThermalReliefGap(mm(0.2))
        z.SetThermalReliefSpokeWidth(mm(0.25))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    print("zones filled")
