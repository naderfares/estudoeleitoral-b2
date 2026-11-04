"""Análise B2 em pedaços: junta as saídas de `b2_tabela.py` nos mesmos arquivos que `ei_bayes.py` grava.

A ordem das linhas segue a de `ei_bayes.main`: UFs em ordem alfabética (ou a da lista --ufs), e dentro de cada UF a
tabela de fluxo antes da de deputado. Para se recusar a juntar uma corrida incompleta, o script para se faltar algum
pedaço.

Uso: python3 -I scripts/b2_juntar.py MUNZONA PEDACOS OUT GOODMAN_N0_20 [--sorteios 200] [--ufs AC,AL]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("munzona", type=Path)
    ap.add_argument("pedacos", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("goodman", type=Path)
    ap.add_argument("--sorteios", type=int, default=200)
    ap.add_argument("--ufs", default="")
    a = ap.parse_args()
    pres = pd.read_csv(a.munzona / "pres_munzona.csv")
    ufs = a.ufs.split(",") if a.ufs else sorted(pres.SG_UF.unique())
    faltam = [f"{uf}_{t}" for uf in ufs for t in ("fluxo", "deputado_blocos")
              if not (a.pedacos / f"{uf}_{t}" / "diagnostico.json").exists()]
    if faltam:
        sys.exit(f"faltam {len(faltam)} pedaços: {', '.join(faltam)}")
    fl, pdp, diag, lim = [], [], [], []
    for uf in ufs:
        for t, destino in (("fluxo", fl), ("deputado_blocos", pdp)):
            p = a.pedacos / f"{uf}_{t}"
            destino.append(pd.read_pickle(p / "sorteios.pkl"))
            lim.append(pd.read_pickle(p / "limites.pkl"))
            diag.append(json.loads((p / "diagnostico.json").read_text()))
    fl = pd.concat(fl, ignore_index=True)
    pdp = pd.concat(pdp, ignore_index=True)
    a.out.mkdir(parents=True, exist_ok=True)
    for k in range(a.sorteios):
        ok = a.out / f"b{k}"
        ok.mkdir(exist_ok=True)
        fl[fl.b == k].drop(columns="b").to_csv(ok / "fluxos_por_uf.csv", index=False)
        pdp[pdp.b == k].drop(columns="b").to_csv(ok / "perfis_deputado_blocos.csv", index=False)
        shutil.copy(a.goodman / "perfis_senado.csv", ok / "perfis_senado.csv")
    pd.DataFrame(diag).to_csv(a.out / "diagnostico_bayes.csv", index=False)
    pd.concat(lim, ignore_index=True).to_csv(a.out / "limites_duncan_davis.csv", index=False)
    print("juntado:", len(ufs), "UFs,", a.sorteios, "sorteios, em", a.out)


if __name__ == "__main__":
    main()
