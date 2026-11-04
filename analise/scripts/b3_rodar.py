"""Análise complementar B3 (dados por seção): refaz a inferência do modelo principal com a seção como unidade e roda
o motor v4 congelado sobre os fluxos e perfis por seção.

Usa o código congelado sem alteração (ei.py, cf.py, motor_v4.py, rodar_preregistro.py), numa raiz alternativa
montada como em B1: as pastas data/ e results/ da análise principal e uma pasta munzona/ com os dados por seção
gerados por b3_preparar.py. Reporta: (1) fluxos e perfis nacionais por seção ao lado dos por zona; (2) a curva de
arrasto por braço com o placebo, como em results4/principal.csv; (3) o índice de H2.

Não há bootstrap: com cerca de 470 mil seções, cada reamostragem refaz a inferência inteira, e as 200 do plano
principal levariam horas. A incerteza de B3 fica descrita pela comparação com a análise principal.

Uso: python3 -I b3_rodar.py RAIZ_B3 RAIZ_PRINCIPAL
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

raiz, princ = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sc = raiz / "scripts"
py = sys.executable
out = raiz / "results_b3"
out.mkdir(exist_ok=True)
log = open(out / "log_b3.txt", "w")
t0 = time.time()

# 1. inferência por seção (âncora N0 = 20, como no modelo principal) e calibração
eo = raiz / "results2_n0_20"
subprocess.run([py, str(sc / "ei.py"), str(raiz / "munzona"), str(eo), "20"], check=True, stdout=log, stderr=log)
subprocess.run([py, str(sc / "cf.py"), str(eo), str(raiz / "data"), str(raiz / "munzona"), str(raiz / "results")],
               check=True, stdout=log, stderr=log)
log.write(f"inferência e calibração: {time.time() - t0:.0f} s\n")

# 2. comparação dos fluxos e perfis nacionais
for nome, chave in (("fluxos_por_uf.csv", ["origem", "destino"]),):
    s = pd.read_csv(eo / nome).groupby(chave).votos.sum().rename("secao")
    z = pd.read_csv(princ / "results2_n0_20" / nome).groupby(chave).votos.sum().rename("zona")
    c = pd.concat([z, s], axis=1).fillna(0)
    c["dif"] = c.secao - c.zona
    c.to_csv(out / "fluxos_nacionais_secao_vs_zona.csv")


def perfil_nacional(pasta, mz):
    pc = pd.read_csv(pasta / "perfis_calibrados.csv", index_col=0)
    pres = pd.read_csv(mz / "pres_munzona.csv")
    pesos = pres.groupby("SG_UF")[["lula1", "flavio1", "outros1", "bn1"]].sum()
    dep = pc[pc.cargo == "deputado"].copy()
    dep["origem"] = dep.index
    linhas = []
    for (uf, o), g in dep.groupby(["uf", "origem"]):
        w = pesos.loc[uf, o]
        for b in ("PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"):
            linhas.append({"origem": o, "bloco": b, "v": g[b].iloc[0] * w, "w": w})
    d = pd.DataFrame(linhas).groupby(["origem", "bloco"]).agg(v=("v", "sum"), w=("w", "sum"))
    return d.v / d.w


ps = perfil_nacional(eo, raiz / "munzona").rename("secao")
pz = perfil_nacional(princ / "results2_n0_20", princ / "munzona").rename("zona")
pc = pd.concat([pz, ps], axis=1)
pc["dif_pp"] = 100 * (pc.secao - pc.zona)
pc.to_csv(out / "perfis_nacionais_secao_vs_zona.csv")

# 3. motor v4 congelado na raiz por seção
os.environ["ESTUDO_ROOT"] = str(raiz)
sys.path.insert(0, str(sc))
import motor_v4 as mv  # noqa: E402
import rodar_preregistro as rp  # noqa: E402

M = mv.carregar(20)
real = rp.cadeiras(mv.run_v4({}, M))
plac = {br: mv.run_v4(rp.cfg(br, placebo=True), M) for br in rp.BRACOS}
prin = []
for br in rp.BRACOS:
    prin.append({"braco": br, "config": "placebo_C", "lam": 0.0, **rp.cadeiras(plac[br])})
    for lam in rp.LAMS:
        r = mv.run_v4(rp.cfg(br, lam=lam), M)
        prin.append({"braco": br, "config": "C+P", "lam": lam, **rp.cadeiras(r), **rp.efeito(r, plac[br]),
                     "sen_flips": r["sen_flips"]})
prin = pd.DataFrame(prin)
prin.to_csv(out / "principal.csv", index=False)

h2 = {}
for i, nome in ((0, "lula"), (1, "flavio")):
    w = np.array([mv.ST[uf]["rows"][i] for uf in mv.UFS])
    f = np.array([M[uf]["P"][i][[mv.ICD, mv.ICM]].sum() / (1 - M[uf]["P"][i][mv.IBN]) for uf in mv.UFS])
    h2[nome] = float((w * f).sum() / w.sum())

pres = pd.read_csv(raiz / "munzona" / "pres_munzona.csv")
presz = pd.read_csv(princ / "munzona" / "pres_munzona.csv")
cols = [c for c in presz.columns if c not in ("SG_UF", "CD_MUNICIPIO", "NR_ZONA")]
tot = {c: {"secao": int(pres[c].sum()), "zona": int(presz[c].sum())} for c in cols if c in pres.columns}
manifesto = {"real": real, "h2": h2, "unidades_secao": int(len(pres)), "unidades_zona": int(len(presz)),
             "totais_presidente": tot, "segundos": round(time.time() - t0)}
(out / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1))
log.close()
print(json.dumps(manifesto, ensure_ascii=False))
