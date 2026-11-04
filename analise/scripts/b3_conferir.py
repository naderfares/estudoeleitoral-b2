"""Confere a conversão por seção (B3): soma as seções por UF e compara com os arquivos por zona da análise principal.

Uso: python3 -I b3_conferir.py MUNZONA_SECAO MUNZONA_ZONA [SAIDA.csv]
"""
import sys
from pathlib import Path

import pandas as pd

S, Z = Path(sys.argv[1]), Path(sys.argv[2])
linhas = []

ps, pz = pd.read_csv(S / "pres_munzona.csv"), pd.read_csv(Z / "pres_munzona.csv")
ufs = sorted(ps.SG_UF.unique())
pz = pz[pz.SG_UF.isin(ufs)]
for c in [c for c in pz.columns if c not in ("SG_UF", "CD_MUNICIPIO", "NR_ZONA")]:
    a, b = pz.groupby("SG_UF")[c].sum(), ps.groupby("SG_UF")[c].sum() if c in ps else 0
    for uf in ufs:
        linhas.append({"arquivo": "pres", "uf": uf, "chave": c, "zona": a.get(uf, 0), "secao": b.get(uf, 0) if c in ps else 0})

for nome, chave, val in (("dep_munzona.csv", "agremiacao", "votos"), ("sen_munzona.csv", "NR_CANDIDATO", "votos"),
                         ("legis_detalhe_munzona.csv", "CD_CARGO", None)):
    s, z = pd.read_csv(S / nome), pd.read_csv(Z / nome)
    z = z[z.SG_UF.isin(ufs)]
    cols = [val] if val else ["QT_COMPARECIMENTO", "bn", "QT_TOTAL_VOTOS_VALIDOS"]
    for col in cols:
        a = z.groupby(["SG_UF", chave])[col].sum()
        b = s.groupby(["SG_UF", chave])[col].sum()
        j = pd.concat([a.rename("zona"), b.rename("secao")], axis=1).fillna(0)
        for (uf, k), r in j.iterrows():
            linhas.append({"arquivo": nome.split("_")[0] + ("" if val else f":{col}"), "uf": uf, "chave": str(k),
                           "zona": r.zona, "secao": r.secao})

d = pd.DataFrame(linhas)
d["dif"] = d.secao - d.zona
if len(sys.argv) > 3:
    d.to_csv(sys.argv[3], index=False)
ruins = d[d.dif != 0]
print(f"{len(d)} somas comparadas; {len(ruins)} diferentes")
if len(ruins):
    print(ruins.sort_values("dif", key=abs, ascending=False).head(30).to_string(index=False))
    tot = d.groupby("arquivo").agg(zona=("zona", "sum"), dif_abs=("dif", lambda x: x.abs().sum()))
    tot["dif_rel"] = tot.dif_abs / tot.zona
    print(tot.to_string())
