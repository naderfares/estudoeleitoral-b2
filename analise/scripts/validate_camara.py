"""Confere se o cálculo reproduz as vagas oficiais por agremiação em cada UF."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seats import distribuir  # noqa: E402

DATA = Path(sys.argv[1])
p = pd.read_csv(DATA / "camara_partidos_2026.csv", keep_default_na=False)
c = pd.read_csv(DATA / "camara_candidatos_2026.csv", keep_default_na=False)
c = c[c.destino_voto.str.startswith("Válido")]

erros = 0
for uf, g in p.groupby("uf"):
    vagas = int(g.vagas_uf.iloc[0])
    vv = int(g.votos_validos_uf.iloc[0])
    agrs = {}
    for ag, gg in g.groupby("agremiacao"):
        agrs[ag] = {"votos": int(gg.votos_total.sum() + gg.votos_legenda.sum()),
                    "cands": c[(c.uf == uf) & (c.agremiacao == ag)].votos.astype(int).tolist()}
    soma = sum(a["votos"] for a in agrs.values())
    res, qe = distribuir(agrs, vagas, vv)
    of = g.drop_duplicates("agremiacao").set_index("agremiacao").vagas_agr_oficial.astype(int).to_dict()
    qe_of = int(g.qe_oficial.iloc[0])
    dif = {k: (res[k], of.get(k, 0)) for k in agrs if res[k] != of.get(k, 0)}
    flag = "OK " if not dif and qe == qe_of else "ERR"
    if flag == "ERR":
        erros += 1
    print(f"{flag} {uf} vagas={vagas} qe={qe} (oficial {qe_of}) soma_agr={soma} vv={vv} difs={dif}")
print("UFs com divergência:", erros)
