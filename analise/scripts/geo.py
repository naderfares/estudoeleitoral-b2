"""Gera caminhos SVG simplificados das UFs (projeção equiretangular com correção de cos(lat))."""
import json
import math
import sys
from pathlib import Path

from shapely.geometry import shape, MultiPolygon, Polygon

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 0.08
X0, Y0, W = 40, 76, 470  # caixa do mapa no SVG

d = json.loads(SRC.read_text())
geoms = {}
for f in d["features"]:
    g = shape(f["geometry"])
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    big = max(p.area for p in polys)
    polys = [p for p in polys if p.area >= max(0.02, 0.01 * big)]  # tira ilhas pequenas
    geoms[f["properties"]["sigla"]] = MultiPolygon(polys)

allb = [g.bounds for g in geoms.values()]
minx, miny = min(b[0] for b in allb), min(b[1] for b in allb)
maxx, maxy = max(b[2] for b in allb), max(b[3] for b in allb)
k = math.cos(math.radians((miny + maxy) / 2))
sx = W / ((maxx - minx) * k)
H = (maxy - miny) * sx


def P(lon, lat):
    return X0 + (lon - minx) * k * sx, Y0 + (maxy - lat) * sx


out = []
total = 0
for uf, g in sorted(geoms.items()):
    gs = g.simplify(TOL, preserve_topology=True)
    polys = list(gs.geoms) if isinstance(gs, MultiPolygon) else [gs]
    parts = []
    for p in polys:
        if p.is_empty:
            continue
        pts = [P(x, y) for x, y in p.exterior.coords]
        s = "M" + "L".join(f"{round(x)} {round(y)}" for x, y in pts[:-1]) + "Z"
        parts.append(s)
    dpath = "".join(parts)
    rp = max(polys, key=lambda q: q.area).representative_point()
    cx, cy = P(rp.x, rp.y)
    c = g.centroid
    ccx, ccy = P(c.x, c.y)
    out.append(dict(uf=uf, d=dpath, cx=round(cx), cy=round(cy), gx=round(ccx), gy=round(ccy)))
    total += len(dpath)
OUT.write_text(json.dumps(out, ensure_ascii=False))
print(f"map box: x {X0}..{X0+W}, y {Y0}..{Y0+H:.0f} | total path chars {total}")
for o in out:
    print(o["uf"], o["cx"], o["cy"], len(o["d"]))
