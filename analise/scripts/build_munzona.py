"""Extrai dados por município/zona (dados abertos TSE 2026) para a inferência ecológica."""
import sys
import zipfile
from pathlib import Path

import pandas as pd

Z = Path(sys.argv[1])
DATA = Path(sys.argv[2])  # onde estão os CSVs da API (para mapear partido -> agremiação)
OUT = Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]


def read(zipname, member, usecols, filt=None, chunksize=500_000):
    z = zipfile.ZipFile(Z / zipname)
    parts = []
    with z.open(member) as f:
        for ch in pd.read_csv(f, sep=";", encoding="latin-1", usecols=usecols, chunksize=chunksize,
                              dtype={"CD_MUNICIPIO": str, "SG_UF": str}, low_memory=False):
            if filt is not None:
                ch = filt(ch)
            parts.append(ch)
    df = pd.concat(parts, ignore_index=True)
    df["CD_MUNICIPIO"] = df.CD_MUNICIPIO.astype(int)
    return df


# ---------- presidente ----------
cols = KEY + ["NR_TURNO", "CD_CARGO", "NR_CANDIDATO", "ST_VOTO_EM_TRANSITO", "QT_VOTOS_NOMINAIS_VALIDOS"]
pc = read("votacao_candidato_munzona_2026.zip", "votacao_candidato_munzona_2026_BR.csv", cols,
          lambda d: d[(d.CD_CARGO == 1) & (d.ST_VOTO_EM_TRANSITO == "N") & (d.SG_UF != "ZZ")])
pc["cat"] = pc.NR_CANDIDATO.map({13: "lula", 22: "flavio"}).fillna("outros")
pres = pc.pivot_table(index=KEY, columns=["NR_TURNO", "cat"], values="QT_VOTOS_NOMINAIS_VALIDOS", aggfunc="sum", fill_value=0)
pres.columns = [f"{c}{t}" for t, c in pres.columns]

dcols = KEY + ["NR_TURNO", "CD_CARGO", "ST_VOTO_EM_TRANSITO", "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
               "QT_VOTOS_BRANCOS", "QT_TOTAL_VOTOS_NULOS", "QT_TOTAL_VOTOS_VALIDOS"]
dp = read("detalhe_votacao_munzona_2026.zip", "detalhe_votacao_munzona_2026_BR.csv", dcols,
          lambda d: d[(d.CD_CARGO == 1) & (d.ST_VOTO_EM_TRANSITO == "N") & (d.SG_UF != "ZZ")])
dp["bn"] = dp.QT_VOTOS_BRANCOS + dp.QT_TOTAL_VOTOS_NULOS
det = dp.pivot_table(index=KEY, columns="NR_TURNO", values=["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "bn"], aggfunc="sum")
det.columns = [{"QT_APTOS": "aptos", "QT_COMPARECIMENTO": "comp", "QT_ABSTENCOES": "abst", "bn": "bn"}[a] + str(t) for a, t in det.columns]
units = pres.join(det, how="inner").reset_index()
units.to_csv(OUT / "pres_munzona.csv", index=False)
print("presidente unidades:", len(units))
print(units[[c for c in units.columns if c not in KEY]].sum().to_string())

# ---------- deputado federal e senado ----------
cp = pd.read_csv(DATA / "camara_partidos_2026.csv", keep_default_na=False)
agr_map = {(r.uf, r.partido): r.agremiacao for r in cp.itertuples()}

dep_rows, sen_rows, ldet_rows = [], [], []
pcols = KEY + ["CD_CARGO", "SG_PARTIDO", "ST_VOTO_EM_TRANSITO", "QT_VOTOS_NOMINAIS_VALIDOS", "QT_TOTAL_VOTOS_LEG_VALIDOS"]
scols = KEY + ["CD_CARGO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "ST_VOTO_EM_TRANSITO", "QT_VOTOS_NOMINAIS_VALIDOS"]
for uf in UFS:
    p = read("votacao_partido_munzona_2026.zip", f"votacao_partido_munzona_2026_{uf}.csv", pcols,
             lambda d: d[(d.CD_CARGO == 6) & (d.ST_VOTO_EM_TRANSITO == "N")])
    p["votos"] = p.QT_VOTOS_NOMINAIS_VALIDOS + p.QT_TOTAL_VOTOS_LEG_VALIDOS
    p["agremiacao"] = [agr_map.get((uf, s), s) for s in p.SG_PARTIDO]
    dep_rows.append(p.groupby(KEY + ["agremiacao"], as_index=False).votos.sum())

    s = read("votacao_candidato_munzona_2026.zip", f"votacao_candidato_munzona_2026_{uf}.csv", scols,
             lambda d: d[(d.CD_CARGO == 5) & (d.ST_VOTO_EM_TRANSITO == "N")])
    sen_rows.append(s.groupby(KEY + ["NR_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"], as_index=False)
                    .QT_VOTOS_NOMINAIS_VALIDOS.sum().rename(columns={"QT_VOTOS_NOMINAIS_VALIDOS": "votos"}))

    d = read("detalhe_votacao_munzona_2026.zip", f"detalhe_votacao_munzona_2026_{uf}.csv", dcols,
             lambda d: d[(d.CD_CARGO.isin([5, 6])) & (d.ST_VOTO_EM_TRANSITO == "N") & (d.NR_TURNO == 1)])
    d["bn"] = d.QT_VOTOS_BRANCOS + d.QT_TOTAL_VOTOS_NULOS
    ldet_rows.append(d.groupby(KEY + ["CD_CARGO"], as_index=False)[["QT_COMPARECIMENTO", "bn", "QT_TOTAL_VOTOS_VALIDOS"]].sum())
    print(uf, "ok", flush=True)

dep = pd.concat(dep_rows, ignore_index=True)
sen = pd.concat(sen_rows, ignore_index=True)
ldet = pd.concat(ldet_rows, ignore_index=True)
dep.to_csv(OUT / "dep_munzona.csv", index=False)
sen.to_csv(OUT / "sen_munzona.csv", index=False)
ldet.to_csv(OUT / "legis_detalhe_munzona.csv", index=False)

# ---------- conferência contra a API ----------
api_agr = cp.assign(v=cp.votos_total + cp.votos_legenda).groupby(["uf", "agremiacao"]).v.sum()
mz_agr = dep.groupby(["SG_UF", "agremiacao"]).votos.sum()
cmp = pd.concat([api_agr.rename("api"), mz_agr.rename("munzona")], axis=1).fillna(0)
cmp["dif"] = cmp.munzona - cmp.api
print("Deputado: maior diferença absoluta munzona x API:", int(cmp.dif.abs().max()), "| soma api", int(cmp.api.sum()), "munzona", int(cmp.munzona.sum()))
sa = pd.read_csv(DATA / "senado_candidatos_2026.csv", keep_default_na=False)
sa = sa[sa.destino_voto.str.startswith("Válido")].groupby(["uf", "numero"]).votos.sum()
sm = sen.groupby(["SG_UF", "NR_CANDIDATO"]).votos.sum()
c2 = pd.concat([sa.rename("api"), sm.rename("munzona")], axis=1).fillna(0)
print("Senado: maior diferença absoluta:", int((c2.munzona - c2.api).abs().max()), "| soma api", int(c2.api.sum()), "munzona", int(c2.munzona.sum()))
