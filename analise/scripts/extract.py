"""Extrai os JSONs da API do TSE (eleição 2026) para CSVs limpos."""
import json
import sys
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

UFS = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to".split()


def n(x):
    return int(x) if x not in (None, "") else 0


def load(f):
    return json.loads((RAW / f).read_text(encoding="utf-8"))


# ---------- Presidente ----------
rows = []
for turno, ele in ((1, "6257"), (2, "6258")):
    for uf in ["br", "zz"] + UFS:
        d = load(f"{uf}-c0001-e00{ele}-u.json")
        v, e = d["v"], d["e"]
        for a in d["carg"][0]["agr"]:
            for p in a["par"]:
                for c in p["cand"]:
                    rows.append(dict(
                        turno=turno, uf=uf.upper(), numero=c["n"], candidato=c["nmu"],
                        partido=p["sg"], votos=n(c["vap"]),
                        votos_validos_uf=n(v["vv"]), brancos=n(v["vb"]), nulos=n(v["tvn"]),
                        comparecimento=n(e["c"]), abstencao=n(e["a"]), eleitorado=n(e["te"]),
                    ))
pres = pd.DataFrame(rows)
pres.to_csv(OUT / "presidente_por_uf_1t_2t.csv", index=False)

# ---------- Senado ----------
rows = []
for uf in UFS:
    d = load(f"{uf}-c0005-e006259-u.json")
    cg = d["carg"][0]
    feds = {f["n"]: f["sg"] for f in cg.get("fed", [])}
    for a in cg["agr"]:
        for p in a["par"]:
            for c in p["cand"]:
                rows.append(dict(
                    uf=uf.upper(), vagas=n(cg["nv"]), numero=c["n"], candidato=c["nmu"],
                    nome_completo=c["nm"], partido=p["sg"], federacao=feds.get(p.get("nfed", ""), ""),
                    coligacao=a.get("nm", ""), composicao_coligacao=a.get("com", ""),
                    tipo_agr=a.get("tp", ""), votos=n(c["vap"]), situacao=c.get("st", ""),
                    eleito=c.get("e") == "s", destino_voto=c.get("dvt", ""),
                    votos_validos_uf=n(d["v"]["vv"]),
                ))
sen = pd.DataFrame(rows)
sen.to_csv(OUT / "senado_candidatos_2026.csv", index=False)

# ---------- Deputado federal ----------
rows_p, rows_c = [], []
for uf in UFS:
    d = load(f"{uf}-c0006-e006259-u.json")
    cg = d["carg"][0]
    feds = {f["n"]: f["sg"] for f in cg.get("fed", [])}
    for a in cg["agr"]:
        # tp 'f' = federação, 'i' = partido isolado
        agr_sigla = a.get("com", "")
        for p in a["par"]:
            rows_p.append(dict(
                uf=uf.upper(), vagas_uf=n(cg["nv"]), qe_oficial=n(cg.get("qe")),
                agremiacao=agr_sigla, tipo_agr=a.get("tp", ""), vagas_agr_oficial=n(a.get("vag")),
                partido=p["sg"], federacao=feds.get(p.get("nfed", ""), ""),
                votos_total=n(p.get("tvtn")), votos_legenda=n(p.get("tvtl")),
                votos_validos_uf=n(d["v"]["vv"]),
            ))
            for c in p["cand"]:
                rows_c.append(dict(
                    uf=uf.upper(), agremiacao=agr_sigla, partido=p["sg"], numero=c["n"],
                    candidato=c["nmu"], votos=n(c["vap"]), situacao=c.get("st", ""),
                    eleito=c.get("e") == "s", destino_voto=c.get("dvt", ""),
                ))
dfp = pd.DataFrame(rows_p)
dfc = pd.DataFrame(rows_c)
dfp.to_csv(OUT / "camara_partidos_2026.csv", index=False)
dfc.to_csv(OUT / "camara_candidatos_2026.csv", index=False)

print("presidente", pres.shape, "senado", sen.shape, "camara partidos", dfp.shape, "camara cand", dfc.shape)
br = pres[pres.uf == "BR"].groupby(["turno", "candidato"]).votos.sum()
print(br[br > 1_000_000])
print("eleitos senado:", sen.eleito.sum())
print("vagas camara (soma oficial por agremiação):",
      dfp.drop_duplicates(["uf", "agremiacao"]).vagas_agr_oficial.sum())
print("eleitos camara (candidatos):", dfc.eleito.sum())
