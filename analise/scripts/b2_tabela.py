"""Análise B2 em pedaços: roda uma tabela (fluxo ou perfil de deputado) de uma UF do modelo bayesiano R×C.

Serve para dividir a corrida de `ei_bayes.py` entre várias máquinas. O modelo, as prioris, o amostrador, as
sementes e a redução a --sorteios sorteios são os de `ei_bayes.py`, cujas funções este script importa sem mudança
(`ajusta`, `limites`, `ipf` e as listas de origens, destinos e blocos). O corpo do laço por UF de `ei_bayes.main`
foi copiado como está, separado nas duas tabelas. `b2_juntar.py` monta, a partir dos pedaços, os mesmos arquivos
que `ei_bayes.py` gravaria; `teste_b2_pedacos.py` confere isso com cadeias curtas.

Uso: python3 -I scripts/b2_tabela.py MUNZONA PEDACOS UF {fluxo,deputado_blocos} [--sorteios 200]
       [--por-cadeia 4000] [--aquecimento 2000] [--cadeias 4] [--semente 2026]
Grava PEDACOS/UF_TABELA/{sorteios.pkl, limites.pkl, diagnostico.json}.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ei_bayes as eb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("munzona", type=Path)
    ap.add_argument("pedacos", type=Path)
    ap.add_argument("uf")
    ap.add_argument("tabela", choices=["fluxo", "deputado_blocos"])
    ap.add_argument("--sorteios", type=int, default=200)
    ap.add_argument("--por-cadeia", type=int, default=4000)
    ap.add_argument("--aquecimento", type=int, default=2000)
    ap.add_argument("--cadeias", type=int, default=4)
    ap.add_argument("--semente", type=int, default=2026)
    a = ap.parse_args()
    mz, uf, por = a.munzona, a.uf, a.por_cadeia
    pres = pd.read_csv(mz / "pres_munzona.csv")

    def reduz(S):
        return S[np.linspace(0, len(S) - 1, a.sorteios).round().astype(int)]
    u = pres[pres.SG_UF == uf].set_index(eb.KEY).sort_index()
    linhas, lim = [], []
    if a.tabela == "fluxo":
        Xc = u[eb.ORIG_T].values
        Tc = u[eb.DEST_T].values
        S, dg = eb.ajusta(Xc, Tc, por, a.aquecimento, a.cadeias, a.semente)
        S = reduz(S)
        lo, hi = eb.limites(Xc, Tc)
        lim += [{"uf": uf, "tabela": "fluxo", "origem": o, "destino": d, "min": lo[i, j], "max": hi[i, j]}
                for i, o in enumerate(eb.ORIG_T) for j, d in enumerate(eb.DEST_T)]
        rt, ct = u[eb.ORIG_T].sum().values.astype(float), u[eb.DEST_T].sum().values.astype(float)
        for k in range(S.shape[0]):
            F = eb.ipf(rt[:, None] * S[k], rt, ct)
            linhas += [{"b": k, "uf": uf, "origem": o, "destino": d, "taxa_ei": S[k, i, j], "votos": F[i, j]}
                       for i, o in enumerate(eb.ORIG_T) for j, d in enumerate(eb.DEST_T)]
    else:
        dep = pd.read_csv(mz / "dep_munzona.csv")
        ldet = pd.read_csv(mz / "legis_detalhe_munzona.csv")
        dep["bloco"] = dep.agremiacao.map(eb.BLOCO).fillna("centro_demais")
        lc = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].set_index(eb.KEY)
        dd = dep[dep.SG_UF == uf].pivot_table(index=eb.KEY, columns="bloco", values="votos", aggfunc="sum", fill_value=0)
        dd["_branco_nulo"] = lc.bn
        dd = dd.reindex(columns=eb.BLOCOS, fill_value=0)
        idx = u.index.intersection(dd.index).intersection(lc.index)
        Xl = u.loc[idx, eb.ORIG_L].values.astype(float)
        Tl = dd.loc[idx].values.astype(float)
        S, dg = eb.ajusta(Xl, Tl, por, a.aquecimento, a.cadeias, a.semente + 1)
        S = reduz(S)
        lo, hi = eb.limites(Xl, Tl)
        lim += [{"uf": uf, "tabela": "deputado_blocos", "origem": o, "destino": g, "min": lo[i, j], "max": hi[i, j]}
                for i, o in enumerate(eb.ORIG_L) for j, g in enumerate(eb.BLOCOS)]
        for k in range(S.shape[0]):
            linhas += [{"b": k, "uf": uf, "origem": o, "bloco": g, "p": S[k, i, j]}
                       for i, o in enumerate(eb.ORIG_L) for j, g in enumerate(eb.BLOCOS)]
    out = a.pedacos / f"{uf}_{a.tabela}"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas).to_pickle(out / "sorteios.pkl")
    pd.DataFrame(lim).to_pickle(out / "limites.pkl")
    (out / "diagnostico.json").write_text(json.dumps({"uf": uf, "tabela": a.tabela, **dg}))
    print(uf, a.tabela, round(dg["rhat_max"], 3), flush=True)


if __name__ == "__main__":
    main()
