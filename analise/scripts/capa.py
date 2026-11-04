import math, random, sys
W, H = 1200, 675
cx, cy, R, r0, rows = 600, 540, 435, 228, 12
blocs = [('lula', 125, '#D9534F'), ('centro', 131, '#CFCBC1'), ('cdir', 139, '#A9C8EE'), ('pl', 118, '#2F6FBF')]
total = sum(b[1] for b in blocs)
radii = [r0 + i*(R-r0)/(rows-1) for i in range(rows)]
raw = [r/sum(radii)*total for r in radii]
n = [int(x) for x in raw]
for i in sorted(range(rows), key=lambda i: raw[i]-n[i], reverse=True)[:total-sum(n)]: n[i] += 1
seats = sorted([(math.pi - (j+0.5)*math.pi/k, r) for r, k in zip(radii, n) for j in range(k)], key=lambda s: (-s[0], s[1]))
assign = [(nm, col) for nm, k, col in blocs for _ in range(k)]
random.seed(11)
def pick(bloc, fr):
    ids = [i for i, a in enumerate(assign) if a[0] == bloc]
    return [ids[int(len(ids)*f)] for f in fr]
hl = set(pick('lula', [0.30, 0.72]) + pick('centro', [0.18, 0.50, 0.83]))
dot, out = 7.0, []
for i, ((a, r), (nm, col)) in enumerate(zip(seats, assign)):
    x, y = cx + r*math.cos(a), cy - r*math.sin(a)
    if i in hl: out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12.5" fill="none" stroke="#1d1d1b" stroke-width="2.6"/>')
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot}" fill="{col}"/>')
leg = [('Coligação de Lula', '125', '+1', '#D9534F'), ('Centro e demais', '131', '+2', '#CFCBC1'),
       ('Centro-direita', '139', '0', '#A9C8EE'), ('PL', '118', '−3', '#2F6FBF')]
legh = ''.join(f'<span class="it"><i style="background:{c}"></i>{l} <b>{v}</b> <em>({d})</em></span>' for l, v, d, c in leg)
page = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0}} #c{{position:relative;width:{W}px;height:{H}px;background:#F5F2EB;font-family:Inter;color:#1d1d1b;overflow:hidden}}
svg{{position:absolute;left:0;top:0}}
.k{{position:absolute;top:40px;width:100%;text-align:center;font:600 16px Inter;letter-spacing:2.4px;color:#6b675f}}
.ctr{{position:absolute;left:0;width:100%;text-align:center}}
.big{{top:{cy-178}px;font:800 108px/1 'Inter Display',Inter;letter-spacing:-3px}} .big small{{font:650 34px 'Inter Display',Inter;letter-spacing:0;margin-left:8px}}
.sub{{top:{cy-62}px;font:500 20px/1.3 Inter;color:#4a4740}}
.lg{{position:absolute;top:{cy+40}px;width:100%;display:flex;justify-content:center;gap:34px;font:500 17px Inter;color:#4a4740}}
.it i{{display:inline-block;width:15px;height:15px;border-radius:50%;margin-right:8px;vertical-align:-2px}} .it b{{color:#1d1d1b}} .it em{{font-style:normal;color:#8a867c}}
.ft{{position:absolute;top:{cy+88}px;width:100%;text-align:center;font:500 13.5px Inter;color:#8a867c}}
.ft s{{display:inline-block;width:11px;height:11px;border:2px solid #1d1d1b;border-radius:50%;text-decoration:none;vertical-align:-3px;margin-right:6px}}
</style></head><body><div id="c">
<svg width="{W}" height="{H}"><line x1="140" y1="{cy+20}" x2="1060" y2="{cy+20}" stroke="#ddd8cc" stroke-width="1.5"/>{''.join(out)}</svg>
<div class="k">ELEIÇÕES 2026 · SE A MOBILIZAÇÃO DO 2º TURNO VIESSE NO 1º</div>
<div class="ctr big">5<small>de 513</small></div>
<div class="ctr sub">cadeiras da Câmara<br>mudariam de mãos</div>
<div class="lg">{legh}</div>
<div class="ft"><s></s>cadeiras que trocariam de bloco · simulação com dados oficiais do TSE</div>
</div></body></html>'''
open(sys.argv[1], 'w', encoding='utf-8').write(page)
