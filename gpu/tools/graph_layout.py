"""Layout and wiring of ComfyUI graphs, used by build_pipeline_graph.py for the pipeline and for the subgraphs inside it.

- Geometry: node boxes and socket heights as the ComfyUI frontend draws them (Vue nodes), measured in the browser and
  kept in comfy_geometry.json; nodes that were not measured fall back to the frontend's rules (20 px per slot row,
  28 px per widget row).
- layout_block: one block of nodes (a pipeline stage or a subgraph's inside) in columns that follow the data flow.
  Each node is set level with the node feeding it when there is room, so most links are straight lines; no node stands
  across a row that a link to another block runs along; a link that skips a column climbs into a channel above the
  nodes instead of running under them.
- place_stages: the stages on a grid, chosen by simulated annealing on an estimate of the whole drawing (every link's
  length and bends weighted by how many links run between the two stages, plus the grid's size).
- Lanes: links run orthogonally through the corridors between columns; the links of one source share one lane (a bus),
  links of different sources never share a path, and the lanes of a corridor are ordered to cross as little as
  possible, each crossing counted per link.
- build_reroutes: the paths as native ComfyUI reroutes (link render mode "Straight").
"""
import itertools
import math
import random

TITLE_H = 30                   # node title bar above the node's pos
LANE_X0, LANE_DX = 30, 22      # first lane and lane pitch of the vertical runs in a corridor between two columns
CHANNEL_DY = 22                # pitch of the horizontal channels links use to skip columns
GAP_X, GAP_Y = 90, 40          # between node columns / stacked nodes inside a block
LEVEL = 6                      # a link whose ends differ by at most this needs no reroute (a jog of a few px at most)


class Geometry:
    """Node boxes and socket heights relative to a node's pos (top of its body; the title is above).
    data: {scope: {node id: {"box": [x0, y0, x1, y1], "ins": {input name: y}, "outs": [y, ...]}}}; scope "root" or a
    subgraph id."""

    def __init__(self, data, scope):
        self.m = (data or {}).get(scope, {})

    def _g(self, n):
        return self.m.get(str(n["id"]))

    def size(self, n):
        if n.get("_io"):
            return tuple(n["size"])
        g = self._g(n)
        if g:
            return (g["box"][2] - g["box"][0], g["box"][3])
        w, h = n.get("size") or [300, 100]
        return (w, max(h, 60))

    def out_y(self, n, slot):
        if n.get("_io"):
            return n["_slots"][slot]
        g = self._g(n)
        if g and slot < len(g["outs"]):
            return g["outs"][slot]
        return 12 + 20 * slot

    def in_y(self, n, slot):
        if n.get("_io"):
            return n["_slots"][slot]
        inp = n["inputs"][slot]
        g = self._g(n)
        if g and inp["name"] in g["ins"]:
            return g["ins"][inp["name"]]
        plain = [i for i in n["inputs"] if not i.get("widget")]
        if not inp.get("widget"):
            return 12 + 20 * plain.index(inp)
        rows = max(len(plain), len(n.get("outputs") or []), 1)
        widgets = [i for i in n["inputs"] if i.get("widget")]
        return 20 * rows + 18 + 28 * widgets.index(inp)


# ---------- lanes ----------

def lane_items(specs, channel_y):
    """specs: (link id, source key, y out, y in, source column, target column, channel key). Returns the lane items
    {(corridor, source, kind[, channel]): [y_start, [y_end, ...]]} (corridor c lies right of column c) and the channel y
    of every link that skips columns (channel_y(channel key, index) gives it)."""
    items, chans, link_chan = {}, {}, {}
    for lid, src, yo, yi, ca, cb, ck in specs:
        if cb - ca == 1:
            if abs(yo - yi) > LEVEL:
                items.setdefault((ca, src, "o"), [yo, []])[1].append(yi)
        else:
            k = chans.setdefault((src, ck), sum(1 for c in chans if c[1] == ck))
            ych = channel_y(ck, k)
            link_chan[lid] = ych
            items.setdefault((ca, src, "o"), [yo, []])[1].append(ych)
            items.setdefault((cb - 1, src, "h", ck), [ych, []])[1].append(yi)
    return items, link_chan


def crossings(order):
    """Crossings of a corridor's lanes, left to right; an item is (y_start, [y_end, ...]). An item's horizontal into its
    lane carries all of its links, so a crossing with it counts once per link."""
    def inside(y, it):
        ys = [it[0]] + list(it[1])
        return min(ys) < y < max(ys)
    c = 0
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            c += inside(order[j][0], order[i]) * len(order[j][1]) + sum(inside(e, order[j]) for e in order[i][1])
            # the right lane's way in and the left lane's way out run side by side between the two lanes: one line
            c += 10 * sum(abs(order[j][0] - e) < 8 for e in order[i][1])
    return c


def best_order(items):
    """The lane order with the fewest crossings: every order for up to 7 lanes, else moves of one lane at a time."""
    if len(items) <= 7:
        return list(min(itertools.permutations(items), key=lambda o: (crossings(o), [it[0] for it in o])))
    best = None
    for key in (lambda l: l[0], lambda l: -l[0], lambda l: sum(l[1]) / len(l[1]), lambda l: -sum(l[1]) / len(l[1])):
        order = sorted(items, key=key)
        improved = True
        while improved:
            improved = False
            for i in range(len(order)):
                for j in range(len(order)):
                    cand = order[:i] + order[i + 1:]
                    cand.insert(j, order[i])
                    if crossings(cand) < crossings(order):
                        order, improved = cand, True
        if best is None or crossings(order) < crossings(best):
            best = order
    return best


def lanes_per_corridor(items):
    n = {}
    for k in items:
        n[k[0]] = n.get(k[0], 0) + 1
    return n


def lane_paths(specs, items, link_chan, corridors, ends):
    """{link id: (source key, [(x, y), ...])}. corridors[c] = (x0, x1) of corridor c; ends[link id] = (x out, x in).
    In the "Straight" render mode ComfyUI draws every piece between two points as horizontal - vertical - horizontal
    with the vertical halfway, so the corners need no reroute: a link whose halfway line falls on its lane gets none,
    any other link one (on its source's or its target's row, which moves the halfway line onto the lane), a link that
    skips columns two (in its channel). Per corridor two arrangements are compared, a crossing counting as two reroutes:
    the lane order with the fewest crossings (a lane takes its own halfway line when that fits the order), and every lane
    on its own halfway line unless it would run along another source's lane."""
    def naturals(c, key):
        mids = [round((ends[s[0]][0] + ends[s[0]][1]) / 2) for s in specs
                if s[1] == key[1] and s[4] == c and s[5] == c + 1 and key[2] == "o"]
        return max(set(mids), key=mids.count) if mids else None

    def span(key):
        ys = [items[key][0]] + list(items[key][1])
        return min(ys), max(ys)

    def score(c, xs):
        order = [(items[k][0], tuple(items[k][1])) for k in sorted(xs, key=xs.get)]
        reroutes = 0
        for k, x in xs.items():
            nat = naturals(c, k)
            reroutes += 2 * len(items[k][1]) if k[2] == "h" or nat is None or abs(nat - x) >= 2 else 0
        return 2 * crossings(order) + reroutes

    lane = {}
    for c in {k[0] for k in items}:
        keys = [k for k in items if k[0] == c]
        x0, x1 = corridors[c]
        ordered, x = {}, x0 + LANE_X0 - LANE_DX           # 1. fewest crossings
        order = best_order([(items[k][0], tuple(items[k][1]), k) for k in keys])
        for i, it in enumerate(order):
            lo, hi = x + LANE_DX, x1 - LANE_X0 - LANE_DX * (len(order) - 1 - i)
            nat = naturals(c, it[2])
            x = nat if nat is not None and lo <= nat <= hi else lo
            ordered[it[2]] = x
        free, placed = {}, []                             # 2. own halfway lines first, the busiest source first
        for k in sorted(keys, key=lambda k: -len(items[k][1])):
            lo_y, hi_y = span(k)
            clash = lambda x: any(abs(x - px) < LANE_DX * 0.7 and lo_y < phi and plo < hi_y for px, plo, phi in placed)
            nat = naturals(c, k)
            cands = ([nat] if nat is not None and x0 + 8 <= nat <= x1 - 8 else []) + \
                    [x0 + LANE_X0 + LANE_DX * i for i in range(int((x1 - x0) // LANE_DX) + 1)]
            x = next((x for x in cands if x <= x1 - 8 and not clash(x)), None)
            if x is None:
                free = None
                break
            free[k] = x
            placed.append((x, lo_y, hi_y))
        best = ordered if free is None or score(c, ordered) <= score(c, free) else free
        lane.update(best)
    paths = {}
    for lid, src, yo, yi, ca, cb, ck in specs:
        xo, xi = ends[lid]
        if cb - ca == 1:
            x = lane.get((ca, src, "o"))
            if abs(yo - yi) <= LEVEL or abs(x - (xo + xi) / 2) < 2:
                pts = []                                   # straight, or its halfway line is its lane
            elif x >= (xo + xi) / 2:
                pts = [(2 * x - xi, yo)]                   # on the source's row
            else:
                pts = [(2 * x - xo, yi)]                   # on the target's row
        else:
            x1, x2, ych = lane[(ca, src, "o")], lane[(cb - 1, src, "h", ck)], link_chan[lid]
            r1, r2 = 2 * x1 - xo, 2 * x2 - xi
            pts = [(r1, ych), (r2, ych)] if xo <= r1 <= r2 <= xi else [(x1, yo), (x1, ych), (x2, ych), (x2, yi)]
        paths[lid] = (src, pts)
    return paths


def _runs_along(a1, b1, a2, b2):
    """Two straight pieces lie on one line (within 6 px) for more than 4 px."""
    h = abs(a1[1] - b1[1]) < 1 and abs(a2[1] - b2[1]) < 1 and abs(a1[1] - a2[1]) < 6
    v = abs(a1[0] - b1[0]) < 1 and abs(a2[0] - b2[0]) < 1 and abs(a1[0] - a2[0]) < 6
    k = 0 if h else 1
    return (h or v) and min(max(a1[k], b1[k]), max(a2[k], b2[k])) - max(min(a1[k], b1[k]), min(a2[k], b2[k])) > 4


def _crosses_box(a, b, boxes, margin=4):
    for x0, y0, x1, y1 in boxes:
        if abs(a[1] - b[1]) < 1:
            lo, hi = sorted((a[0], b[0]))
            if y0 + margin < a[1] < y1 - margin and lo < x1 - margin and hi > x0 + margin:
                return True
        else:
            lo, hi = sorted((a[1], b[1]))
            if x0 + margin < a[0] < x1 - margin and lo < y1 - margin and hi > y0 + margin:
                return True
    return False


def simplify(paths, ends_xy, boxes):
    """Drop every reroute that is not needed: a link whose plain path (the one ComfyUI draws without reroutes) crosses
    no node box and runs along no link of another source keeps no reroutes. boxes: (x0, y0, x1, y1) of every node,
    title included. Changes paths in place; returns how many reroute points went."""
    cur = {lid: drawn_pieces({lid: paths[lid]}, ends_xy) for lid in paths if lid in ends_xy}
    dropped = 0

    import os
    debug = os.environ.get("LAYOUT_DEBUG")

    def free(lid, src, pts):
        pcs = drawn_pieces({lid: (src, pts)}, ends_xy)
        hit = next(((a, b, bx) for _, _, a, b in pcs for bx in boxes if _crosses_box(a, b, [bx])), None)
        if hit:
            if debug and not pts:
                print(f"    link {lid}: plain path crosses box {[round(v) for v in hit[2]]} at {hit[0]}->{hit[1]}")
            return None
        along = next(((l2, c, d) for l2, segs in cur.items() if l2 != lid and paths[l2][0] != src
                      for _, _, c, d in segs for _, _, a, b in pcs if _runs_along(a, b, c, d)), None)
        if along:
            if debug and not pts:
                print(f"    link {lid}: plain path runs along link {along[0]} at {along[1]}->{along[2]}")
            return None
        return pcs

    def length(pcs):
        return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for _, _, a, b in pcs)

    # links of one source that share their first reroute run as one bus: they are simplified together, and only into
    # paths that still share their vertical (the same halfway line), so the bus stays one line
    groups = {}
    for lid in cur:
        src, pts = paths[lid]
        if pts:
            groups.setdefault((src, pts[0]), []).append(lid)
    for members in groups.values():
        if len(members) < 2:
            continue
        src = paths[members[0]][0]
        plains = [free(l, src, []) for l in members]
        mids = {round((ends_xy[l][0][0] + ends_xy[l][1][0]) / 2) for l in members}
        if all(p is not None for p in plains) and max(mids) - min(mids) < 2:
            for l, p in zip(members, plains):
                dropped += len(paths[l][1])
                paths[l], cur[l] = (src, []), p

    solo = {l for ms in groups.values() if len(ms) == 1 for l in ms}
    for lid in sorted(cur, key=lambda l: -len(paths[l][1])):
        src, pts = paths[lid]
        if not pts or lid not in solo:
            continue
        best = free(lid, src, [])
        if best is not None:                         # a plain link
            chosen = []
        elif len(pts) > 1:                           # one reroute instead of several
            (xo, yo), (xi, yi) = ends_xy[lid]
            ys = sorted({yo, yi} | {p[1] for p in pts})
            lo, hi = min(xo, xi), max(xo, xi)
            chosen = None
            for ry in ys:
                for k in range(int((hi - lo) // 11) + 1):
                    cand = [(lo + 11 * k, ry)]
                    pcs = free(lid, src, cand)
                    if pcs is not None and (best is None or length(pcs) < length(best)):
                        best, chosen = pcs, cand
            if chosen is None:
                continue
        else:
            continue
        dropped += len(pts) - len(chosen)
        paths[lid] = (src, chosen)
        cur[lid] = best
    return dropped


def drawn_pieces(paths, ends_xy):
    """The horizontal and vertical pieces ComfyUI draws for every link, as (link id, source key, a, b): between each two
    points horizontal - vertical (halfway) - horizontal. ends_xy[link id] = ((x, y) out, (x, y) in)."""
    out = []
    for lid, (src, pts) in paths.items():
        p = [ends_xy[lid][0]] + list(pts) + [ends_xy[lid][1]]
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            if abs(ay - by) < 1:
                out.append((lid, src, (ax, ay), (bx, by)))
                continue
            m = (ax + bx) / 2
            out += [(lid, src, (ax, ay), (m, ay)), (lid, src, (m, ay), (m, by)), (lid, src, (m, by), (bx, by))]
    return out


# ---------- one block ----------

def layout_block(nodes, links, geo, exports=(), imports=(), io_in=None, io_out=None):
    """Place nodes relative to (0, 0) and route the links between them.
    links: (link id, origin id, origin slot, target id, target slot); only links inside the block are routed.
    exports / imports: (node id, slot) of sockets wired to other blocks (to the right / from the left): no node of the
    block stands across their row on that side. io_in / io_out: a subgraph's input and output nodes (pseudo nodes with
    "_io", "size" and "_slots"); they take the first and the last column.
    Returns (width, height, {link id: (source key, points)})."""
    flow = list(nodes) + [n for n in (io_in, io_out) if n]
    by_id = {n["id"]: n for n in flow}
    own = [l for l in links if l[1] in by_id and l[3] in by_id]
    preds = {i: [] for i in by_id}
    succs = {i: [] for i in by_id}
    for l in own:
        preds[l[3]].append(l)
        succs[l[1]].append(l)
    depth = {i: 0 for i in by_id}
    if io_in:
        for i in by_id:
            depth[i] = 0 if i == io_in["id"] else 1
    for _ in range(len(by_id)):
        for l in own:
            if io_out and l[3] == io_out["id"]:
                continue
            depth[l[3]] = max(depth[l[3]], depth[l[1]] + 1)
    moved = True
    while moved:                                     # every node moves right up to its first consumer: fewer skipping links
        moved = False
        for i in sorted(by_id, key=lambda i: -depth[i]):
            nxt = [depth[l[3]] for l in succs[i] if not (io_out and l[3] == io_out["id"])]
            if nxt and not by_id[i].get("_io") and min(nxt) - 1 > depth[i]:
                depth[i], moved = min(nxt) - 1, True
    if io_out:
        depth[io_out["id"]] = max(d for i, d in depth.items() if i != io_out["id"]) + 1
    cols = {}
    for n in sorted(flow, key=lambda n: n["pos"][1] if not n.get("_io") else 0):
        cols.setdefault(depth[n["id"]], []).append(n)
    ncol = max(cols) + 1
    for _ in range(2):                               # order each column by the mean position of its sources
        rank = {n["id"]: i for c in cols.values() for i, n in enumerate(c)}
        for d in sorted(cols):
            cols[d].sort(key=lambda n: sum(rank[l[1]] for l in preds[n["id"]]) / len(preds[n["id"]])
                         if preds[n["id"]] else rank[n["id"]] - 0.5)
            rank.update({n["id"]: i for i, n in enumerate(cols[d])})

    skip_src = {(l[1], l[2]) for l in own if depth[l[3]] - depth[l[1]] > 1}
    top = TITLE_H + (30 + CHANNEL_DY * len(skip_src) if skip_src else 0)

    # one pass, left to right: the columns on the left are final when a column is placed, and only the node being
    # placed moves (down), so two nodes never push each other back and forth
    pos_y = {}
    for d in sorted(cols):
        left = [m for c in sorted(cols) if c < d for m in cols[c]]
        out_rows = [pos_y[m["id"]] + geo.out_y(m, s) for m in left for s in range(len(m.get("outputs") or []))
                    if (m["id"], s) in exports]      # wires to other blocks run right through this column
        spans = [(pos_y[m["id"]] - TITLE_H - 12, pos_y[m["id"]] + geo.size(m)[1] + 12) for m in left]
        cursor = top
        for n in cols[d]:
            h = geo.size(n)[1]
            y = cursor
            lp = sorted((l for l in preds[n["id"]] if l[1] in pos_y), key=lambda l: (depth[n["id"]] - depth[l[1]] != 1, l[4]))
            if lp:                                   # level with the source of its first input
                y = max(y, pos_y[lp[0][1]] + geo.out_y(by_id[lp[0][1]], lp[0][2]) - geo.in_y(n, lp[0][4]))
            in_rows = [geo.in_y(n, s) for s in range(len(n.get("inputs") or [])) if (n["id"], s) in imports]
            moved = True
            while moved:
                moved = False
                for r in out_rows:                   # a wire out of a node on the left must pass this node
                    if y - TITLE_H - 12 < r < y + h + 12:
                        y, moved = r + 12 + TITLE_H, True
                for r in in_rows:                    # a wire into this node from another block must pass the nodes on the left
                    for lo, hi in spans:
                        if lo < y + r < hi:
                            y, moved = hi - r + 1, True
            pos_y[n["id"]] = y
            cursor = y + h + GAP_Y + TITLE_H

    specs = [(l[0], (l[1], l[2]), pos_y[l[1]] + geo.out_y(by_id[l[1]], l[2]),
              pos_y[l[3]] + geo.in_y(by_id[l[3]], l[4]), depth[l[1]], depth[l[3]], 0) for l in own]
    items, link_chan = lane_items(specs, lambda ck, k: top - TITLE_H - 15 - CHANNEL_DY * k)
    need = lanes_per_corridor(items)
    col_x, col_w, x = {}, {}, 0
    for d in range(ncol):
        col_x[d] = x
        col_w[d] = max((geo.size(n)[0] for n in cols.get(d, [])), default=0)
        x += col_w[d] + max(GAP_X, 2 * LANE_X0 + LANE_DX * need.get(d, 0))
    for d, c in cols.items():
        for n in c:
            n["pos"] = [col_x[d], pos_y[n["id"]]]
    width = max(col_x[d] + col_w[d] for d in cols)
    height = max(pos_y[n["id"]] + geo.size(n)[1] for n in flow)
    corridors = {d: (col_x[d] + col_w[d], col_x[d + 1] if d + 1 < ncol else col_x[d] + col_w[d] + GAP_X) for d in range(ncol)}
    ends = {l[0]: (col_x[depth[l[1]]] + geo.size(by_id[l[1]])[0], col_x[depth[l[3]]]) for l in own}
    paths = lane_paths(specs, items, link_chan, corridors, ends)
    return width, height, paths


# ---------- stages on a grid ----------

def place_stages(init, weights, box, max_col=5, rows=3, seed=7, steps=60000):
    """Cells {stage: (column, row)} minimising, for every pair of linked stages, the links' length (rows apart, columns
    skipped) and bends times the number of links between them, plus the grid's size from the stages' boxes. A link must
    run left to right. Simulated annealing from `init`, deterministic."""
    rnd = random.Random(seed)
    keys = sorted(init)

    def cost(st):
        c = 0.0
        for (s, t), w in weights.items():
            (cs, rs), (ct, rt) = st[s], st[t]
            if ct <= cs:
                return float("inf")
            c += w * (abs(rs - rt) * 1200 + (ct - cs - 1) * 1600 + (0 if rs == rt and ct - cs == 1 else 400))
        colw, rowh = {}, {}
        for k, (cc, rr) in st.items():
            colw[cc] = max(colw.get(cc, 0), box[k][0])
            rowh[rr] = max(rowh.get(rr, 0), box[k][1])
        return c + sum(colw.values()) + 300 * len(colw) + sum(rowh.values())

    st = dict(init)
    if cost(st) == float("inf"):                      # the hint breaks the flow: start from the data-flow layers
        layer = {k: 0 for k in keys}
        for _ in keys:
            for (s, t) in weights:
                layer[t] = max(layer[t], layer[s] + 1)
        per = {}
        for k in sorted(keys, key=lambda k: init[k][1]):
            per.setdefault(layer[k], []).append(k)
        rows = max(rows, max(len(v) for v in per.values()))
        max_col = max(max_col, len(per))
        st = {k: (layer[k] + 1, i) for l, ks in per.items() for i, k in enumerate(ks)}
    cur = cost(st)
    best, best_c, temp = dict(st), cur, 4000.0
    for _ in range(steps):
        k = rnd.choice(keys)
        cell = (rnd.randint(1, max_col), rnd.randrange(rows))
        other = next((o for o in keys if st[o] == cell), None)
        new = dict(st)
        new[k] = cell
        if other:
            new[other] = st[k]
        c = cost(new)
        if c < cur or (c < float("inf") and rnd.random() < math.exp((cur - c) / temp)):
            st, cur = new, c
            if c < best_c:
                best, best_c = dict(new), c
        temp = max(1.0, temp * 0.9998)
    remap = {c: i + 1 for i, c in enumerate(sorted({c for c, _ in best.values()}))}
    rremap = {r: i for i, r in enumerate(sorted({r for _, r in best.values()}))}
    return {k: (remap[c], rremap[r]) for k, (c, r) in best.items()}, best_c


# ---------- output ----------

def build_reroutes(paths, first_id=1):
    """Native reroutes and each link's last reroute: (reroutes, {link id: last reroute id}). Links of one source share
    the reroutes of their common path, so a bus is drawn as one line."""
    reroutes, last, shared = [], {}, {}
    for lid, (src, pts) in sorted(paths.items()):
        parent = None
        for i, pt in enumerate(pts):
            sid = (src, tuple(pts[: i + 1]))
            r = shared.get(sid)
            if r is None:
                r = {"id": first_id + len(reroutes), "pos": [round(pt[0], 1), round(pt[1], 1)], "linkIds": []}
                if parent:
                    r["parentId"] = parent["id"]
                shared[sid] = r
                reroutes.append(r)
            r["linkIds"].append(lid)
            parent = r
        if parent:
            last[lid] = parent["id"]
    return reroutes, last


def segments(paths, ends):
    """Straight pieces of every routed link: (link id, source key, a, b); ends[link id] = (out point, in point)."""
    out = []
    for lid, (src, pts) in paths.items():
        p = [ends[lid][0]] + list(pts) + [ends[lid][1]]
        out += [(lid, src, a, b) for a, b in zip(p, p[1:])]
    return out


def overlaps(segs):
    """Pieces of links of different sources that run over each other (a shared source is a bus, which is fine)."""
    found = []
    for i, (l1, s1, a1, b1) in enumerate(segs):
        for l2, s2, a2, b2 in segs[i + 1:]:
            if s1 == s2:
                continue
            h = abs(a1[1] - b1[1]) < 1 and abs(a2[1] - b2[1]) < 1 and abs(a1[1] - a2[1]) < 6
            v = abs(a1[0] - b1[0]) < 1 and abs(a2[0] - b2[0]) < 1 and abs(a1[0] - a2[0]) < 6
            k = 0 if h else 1
            if (h or v) and min(max(a1[k], b1[k]), max(a2[k], b2[k])) - max(min(a1[k], b1[k]), min(a2[k], b2[k])) > 4:
                found.append((l1, l2, a1, a2))
    return found
