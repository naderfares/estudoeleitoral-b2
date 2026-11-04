"""Gera o código dos dois widgets de mapa (virada por UF e mudanças no Congresso)."""
import json
import sys
from pathlib import Path

geo = {g["uf"]: g for g in json.loads(Path(sys.argv[1]).read_text())}
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

swing = {"RJ": 4.25, "SP": 3.77, "GO": 3.65, "AL": 3.27, "SC": 3.27, "MS": 3.22, "RR": 3.2, "PR": 3.18, "MG": 3.12,
         "DF": 3.1, "RS": 3.06, "MT": 3.0, "AP": 2.85, "ES": 2.83, "RO": 2.65, "AC": 2.64, "RN": 2.51, "PB": 2.51,
         "TO": 2.37, "SE": 2.33, "AM": 2.28, "PA": 2.15, "MA": 2.1, "PE": 2.04, "CE": 2.0, "BA": 1.44, "PI": 1.21}
# rótulos fora do mapa (estados pequenos), ordenados de cima para baixo
CALL = {"RN": 205, "PB": 231, "PE": 257, "AL": 283, "SE": 309, "DF": 343, "ES": 384, "RJ": 414}
AJUSTE = {"GO": (316, 352), "MG": (392, 368), "PI": (420, 236), "SC": (330, 484)}
LX = 548


def q(s):
    return s.replace("'", "\\'")


rowsA = []
for uf in sorted(geo):
    g = geo[uf]
    call = uf in CALL
    lx, ly = (LX, CALL[uf]) if call else AJUSTE.get(uf, (g["cx"], g["cy"]))
    rowsA.append(f"{{uf:'{uf}', pp:{swing[uf]}, cx:{g['cx']}, cy:{g['cy']}, lx:{lx}, ly:{ly}, ext:{1 if call else 0}, d:'{g['d']}'}}")

codeA = (
    "export default () => <claude.Visualize data-claude-component='mapa-virada' sources={{rows:{kind:'data', data:["
    + ",".join(rowsA)
    + "]}, nac:{kind:'data', data:[{pais:'Brasil', pp:2.8}]}}}>{({rows, nac, datum}) => { "
    "const lo = Math.min(...rows.map(r => r.pp)), hi = Math.max(...rows.map(r => r.pp)); "
    "const op = v => 0.1 + (v - lo) / (hi - lo) * 0.75; "
    "const fmt = v => `+${v.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1})}`; "
    "const n0 = nac.at(0); const passos = [0, 1, 2, 3, 4].map(k => lo + k * (hi - lo) / 4); "
    "return <svg viewBox='0 0 760 596' role='img' aria-label='Lula cresceu em todos os estados, mais no Centro-Sul que no Nordeste' fontSize='11'>"
    "<text data-claude-text-id='title' x='24' y='28' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>Lula cresceu em todos os estados, mais no Centro-Sul que no Nordeste</text>"
    "<text data-claude-text-id='subtitle' x='24' y='50' fontSize='12' fill='var(--cds-text-secondary)'>Variação da fatia de Lula no voto Lula + Flávio, do 1º para o 2º turno (pontos percentuais)</text>"
    "<g data-claude-anchor='estados'>{rows.map(r => <path key={r.uf} d={r.d} fill='var(--cds-chart-categorical-1)' fillOpacity={op(r.pp)} stroke='var(--cds-chart-axis)' strokeWidth='0.6' strokeLinejoin='round' {...datum(r, 'pp')}><title>{`${r.uf}: ${fmt(r.pp)} pontos`}</title></path>)}</g>"
    "<g data-claude-anchor='rotulos'>{rows.map(r => r.ext ? <g key={r.uf}><path d={`M${r.cx} ${r.cy}L${r.lx - 8} ${r.ly - 4}`} fill='none' stroke='var(--cds-text-secondary)' strokeWidth='0.75'/><circle cx={r.cx} cy={r.cy} r='1.8' fill='var(--cds-text-primary)'/><text x={r.lx} y={r.ly} fontSize='11.5' fill='var(--cds-text-primary)' {...datum(r, 'pp')}><tspan fontWeight='600'>{r.uf}</tspan>{` ${fmt(r.pp)}`}</text></g> : <g key={r.uf}><text x={r.lx} y={r.ly - 1} textAnchor='middle' fontSize='11' fontWeight='600' fill='var(--cds-text-primary)'>{r.uf}</text><text x={r.lx} y={r.ly + 11} textAnchor='middle' fontSize='10.5' fill='var(--cds-text-primary)' {...datum(r, 'pp')}>{fmt(r.pp)}</text></g>)}</g>"
    "<g data-claude-anchor='legenda'><text data-claude-text-id='leg-titulo' x='548' y='478' fontSize='11.5' fontWeight='600' fill='var(--cds-text-primary)'>Variação, em pontos</text>{passos.map((v, k) => <rect key={k} x={548 + k * 34} y='488' width='32' height='12' fill='var(--cds-chart-categorical-1)' fillOpacity={op(v)} stroke='var(--cds-chart-axis)' strokeWidth='0.5'/>)}<text x='548' y='516' fontSize='11' fill='var(--cds-text-secondary)'>{fmt(lo)}</text><text x='714' y='516' textAnchor='end' fontSize='11' fill='var(--cds-text-secondary)'>{fmt(hi)}</text><text x='548' y='540' fontSize='11.5' fill='var(--cds-text-primary)' {...datum(n0, 'pp')}><tspan fontWeight='600'>{n0.pais}</tspan>{`: ${fmt(n0.pp)}`}</text></g>"
    "</svg>; }}</claude.Visualize>;"
)

# ---------- mapa B: mudanças no Congresso ----------
MUD = {"SP": ("pl", "Câmara", "PL −1, PT +1", 1), "RJ": ("pl", "Câmara", "PL −1, MDB +1", 2),
       "AM": ("pl", "Câmara", "PL −1, PSD +1", 3), "MA": ("troca", "Câmara", "PCdoB −1, MDB +1", 4),
       "RS": ("troca", "Câmara", "MDB −1, PT +1", 5), "RN": ("troca", "Senado", "PT −1, PSD +1 (empate técnico)", 6)}
LBL_B = {"RJ": (458, 446, 1), "RN": (512, 206, 1)}
rowsB = []
for uf in sorted(geo):
    g = geo[uf]
    cat, casa, txt, ordem = MUD.get(uf, ("", "", "", 0))
    lx, ly, call = LBL_B.get(uf, (g["cx"], g["cy"], 0))
    rowsB.append(f"{{uf:'{uf}', cat:'{cat}', casa:'{casa}', txt:'{q(txt)}', ordem:{ordem}, cx:{g['cx']}, cy:{g['cy']}, lx:{lx}, ly:{ly}, ext:{call}, d:'{g['d']}'}}")

codeB = (
    "export default () => <claude.Visualize data-claude-component='mapa-mudancas' sources={{rows:{kind:'data', data:["
    + ",".join(rowsB)
    + "]}}}>{({rows, datum}) => { "
    "const cor = c => c === 'pl' ? 'var(--cds-chart-categorical-2)' : 'var(--cds-chart-muted)'; "
    "const op = c => c === 'pl' ? 0.6 : c === 'troca' ? 0.95 : 0.18; "
    "const lista = rows.filter(r => r.ordem > 0).sort((a, b) => a.ordem - b.ordem); "
    "return <svg viewBox='0 0 760 576' role='img' aria-label='O PL perderia cadeiras em SP, RJ e AM; o resto seriam trocas pontuais' fontSize='11'>"
    "<text data-claude-text-id='title' x='24' y='28' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>O PL perderia cadeiras em SP, RJ e AM; o resto seriam trocas pontuais</text>"
    "<text data-claude-text-id='subtitle' x='24' y='50' fontSize='12' fill='var(--cds-text-secondary)'>Estados onde a Câmara ou o Senado mudariam se o movimento da virada acontecesse no 1º turno</text>"
    "<g data-claude-anchor='estados'>{rows.map(r => <path key={r.uf} d={r.d} fill={cor(r.cat)} fillOpacity={op(r.cat)} stroke='var(--cds-chart-axis)' strokeWidth='0.6' strokeLinejoin='round' {...datum(r, 'txt')}><title>{r.ordem > 0 ? `${r.uf}, ${r.casa}: ${r.txt}` : `${r.uf}: sem mudança`}</title></path>)}</g>"
    "<g data-claude-anchor='rotulos'>{lista.map(r => r.ext ? <g key={r.uf}><path d={`M${r.cx} ${r.cy}L${r.lx - 4} ${r.ly - 4}`} fill='none' stroke='var(--cds-text-secondary)' strokeWidth='0.75'/><text x={r.lx} y={r.ly} fontSize='11.5' fontWeight='600' fill='var(--cds-text-primary)' {...datum(r, 'uf')}>{r.uf}</text></g> : <text key={r.uf} x={r.lx} y={r.ly + 4} textAnchor='middle' fontSize='11.5' fontWeight='600' fill='var(--cds-text-primary)' {...datum(r, 'uf')}>{r.uf}</text>)}</g>"
    "<g data-claude-anchor='painel'><rect x='548' y='120' width='12' height='12' rx='2' fill={cor('pl')} fillOpacity={op('pl')}/><text data-claude-text-id='leg-pl' x='566' y='130' fontSize='11.5' fill='var(--cds-text-primary)'>PL perde 1 deputado</text><rect x='548' y='142' width='12' height='12' rx='2' fill={cor('troca')} fillOpacity={op('troca')}/><text data-claude-text-id='leg-troca' x='566' y='152' fontSize='11.5' fill='var(--cds-text-primary)'>Troca entre outros partidos</text>"
    "{lista.map((r, k) => <g key={r.uf}><text x='548' y={196 + k * 40} fontSize='12' fontWeight='600' fill='var(--cds-text-primary)' {...datum(r, 'casa')}>{`${r.uf} · ${r.casa}`}</text><text x='548' y={212 + k * 40} fontSize='11' fill='var(--cds-text-secondary)' {...datum(r, 'txt')}>{r.txt}</text></g>)}</g>"
    "</svg>; }}</claude.Visualize>;"
)
(OUT / "mapA.txt").write_text(codeA)
(OUT / "mapB.txt").write_text(codeB)
print(len(codeA), len(codeB))
