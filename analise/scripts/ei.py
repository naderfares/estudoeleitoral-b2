"""Inferência ecológica por UF (unidades = município/zona), com regularização.

1) Fluxo 1º -> 2º turno (presidente): origens {lula1, flavio1, outros1, bn1, abst1} -> destinos
   {lula2, flavio2, bn2, abst2}. Regressão de Goodman restrita (taxas em [0,1], cada origem soma 1),
   ponderada pelo eleitorado, encolhida para a estimativa nacional (equivale a N0 pseudo-unidades),
   e depois calibrada (IPF) para bater exatamente com os totais reais da UF.
2) Perfil legislativo dos eleitores de cada categoria do 1º turno {lula1, flavio1, outros1, bn1}:
   - deputado federal por BLOCO (PL, coligação Lula, centro-direita, centro e demais, branco/nulo);
   - senador por candidato (candidatos com < 5% agrupados), 2 votos por eleitor.
   Encolhidos para o perfil médio da UF (ninguém difere de ninguém) com N0 pseudo-unidades.
"""
import sys
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd

MZ = Path(sys.argv[1])
OUT = Path(sys.argv[2])
N0 = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
OUT.mkdir(parents=True, exist_ok=True)
KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]
ORIG_T = ["lula1", "flavio1", "outros1", "bn1", "abst1"]
DEST_T = ["lula2", "flavio2", "bn2", "abst2"]
ORIG_L = ["lula1", "flavio1", "outros1", "bn1"]

BLOCO = {"PL": "PL",
         "PCDOB / PT / PV": "coligacao_lula", "PSOL / REDE": "coligacao_lula", "PSB": "coligacao_lula", "PDT": "coligacao_lula",
         "NOVO": "centro_direita", "MISSÃO": "centro_direita", "PP / UNIÃO": "centro_direita", "REPUBLICANOS": "centro_direita"}
BLOCOS = ["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]

pres = pd.read_csv(MZ / "pres_munzona.csv")
dep = pd.read_csv(MZ / "dep_munzona.csv")
sen = pd.read_csv(MZ / "sen_munzona.csv")
ldet = pd.read_csv(MZ / "legis_detalhe_munzona.csv")
dep["bloco"] = dep.agremiacao.map(BLOCO).fillna("centro_demais")


def solve(X, Y, w, row_sum=1.0, ub=None, prior=None, n0=0.0):
    """min  sum_m w_m ||Y_m - X_m P||^2 / sum w  +  (n0/n) * sum_k var_k ||P_k - prior_k||^2"""
    n, k = X.shape
    g = Y.shape[1]
    P = cp.Variable((k, g))
    sw = np.sqrt(w / w.sum())[:, None]
    obj = cp.sum_squares(cp.multiply(sw, Y - X @ P))
    if prior is not None and n0 > 0:
        # peso proporcional à variância de cada coluna de X entre unidades (informação que os
        # dados trazem sobre P): n0 pseudo-unidades de informação
        xbar = (w[:, None] * X).sum(0) / w.sum()
        v = (w[:, None] * (X - xbar) ** 2).sum(0) / w.sum()
        obj = obj + (n0 / n) * cp.sum(cp.multiply(v[:, None], cp.square(P - prior)))
    cons = [P >= 0, cp.sum(P, axis=1) == row_sum]
    if ub is not None:
        cons.append(P <= ub)
    cp.Problem(cp.Minimize(obj), cons).solve(solver=cp.CLARABEL)
    return np.clip(P.value, 0, None)


def ipf(seed, row_tot, col_tot, it=1000):
    M = seed.copy() + 1e-9
    col_tot = col_tot * row_tot.sum() / col_tot.sum()
    for _ in range(it):
        M *= (row_tot / M.sum(1))[:, None]
        M *= (col_tot / M.sum(0))[None, :]
    return M


def r2(Y, Yhat, w):
    ybar = (w[:, None] * Y).sum(0) / w.sum()
    ss_res = (w[:, None] * (Y - Yhat) ** 2).sum(0)
    ss_tot = (w[:, None] * (Y - ybar) ** 2).sum(0)
    return 1 - ss_res / np.where(ss_tot > 0, ss_tot, np.nan)


# prior nacional para o fluxo
Xn = pres[ORIG_T].div(pres.aptos1, axis=0).values
Yn = pres[DEST_T].div(pres.aptos2, axis=0).values
theta_nac = solve(Xn, Yn, pres.aptos1.values.astype(float))

fluxos, perf_dep, perf_sen, diag = [], [], [], []
for uf, u in pres.groupby("SG_UF"):
    u = u.set_index(KEY).sort_index()
    nu = len(u)

    # ---------- 1) fluxo ----------
    X = u[ORIG_T].div(u.aptos1, axis=0).values
    Y = u[DEST_T].div(u.aptos2, axis=0).values
    w = u.aptos1.values.astype(float)
    theta = solve(X, Y, w, prior=theta_nac, n0=N0)
    F = ipf(u[ORIG_T].sum().values[:, None] * theta, u[ORIG_T].sum().values.astype(float), u[DEST_T].sum().values.astype(float))
    for i, o in enumerate(ORIG_T):
        for j, d in enumerate(DEST_T):
            fluxos.append(dict(uf=uf, origem=o, destino=d, taxa_ei=theta[i, j], votos=F[i, j]))
    diag.append(dict(uf=uf, etapa="fluxo", unidades=nu, r2_medio=float(np.nanmean(r2(Y, X @ theta, w)))))

    # ---------- 2a) deputado por bloco ----------
    lc = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].set_index(KEY)
    d = dep[dep.SG_UF == uf].pivot_table(index=KEY, columns="bloco", values="votos", aggfunc="sum", fill_value=0)
    d["_branco_nulo"] = lc.bn
    d = d.reindex(columns=BLOCOS, fill_value=0)
    idx = u.index.intersection(d.index).intersection(lc.index)
    comp = lc.loc[idx, "QT_COMPARECIMENTO"].astype(float)
    S = u.loc[idx, ORIG_L].div(u.loc[idx, ORIG_L].sum(axis=1), axis=0).values
    Z = d.loc[idx].div(comp, axis=0).values
    prior = np.tile((d.loc[idx].sum() / comp.sum()).values, (len(ORIG_L), 1))
    prior = prior / prior.sum(1, keepdims=True)
    P = solve(S, Z, comp.values, prior=prior, n0=N0)
    for i, o in enumerate(ORIG_L):
        for j, g in enumerate(BLOCOS):
            perf_dep.append(dict(uf=uf, origem=o, bloco=g, p=P[i, j]))
    rr = r2(Z, S @ P, comp.values)
    diag.append(dict(uf=uf, etapa="deputado_blocos", unidades=len(idx), r2_medio=float(np.nanmean(rr[:4])),
                     r2_PL=rr[0], r2_colig_lula=rr[1]))

    # ---------- 2b) senado por candidato ----------
    ls = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 5)].set_index(KEY)
    s = sen[sen.SG_UF == uf].pivot_table(index=KEY, columns="NR_CANDIDATO", values="votos", aggfunc="sum", fill_value=0)
    stot = s.sum()
    sg = stot[stot / stot.sum() >= 0.05].index.tolist()
    sgdf = s[sg].copy()
    sp = [c for c in s.columns if c not in sg]
    if sp:
        sgdf["_outros"] = s[sp].sum(axis=1)
    sgdf["_branco_nulo"] = ls.bn
    idx = u.index.intersection(sgdf.index).intersection(ls.index)
    comp_s = ls.loc[idx, "QT_COMPARECIMENTO"].astype(float)
    S = u.loc[idx, ORIG_L].div(u.loc[idx, ORIG_L].sum(axis=1), axis=0).values
    Z = sgdf.loc[idx].div(comp_s, axis=0).values
    ub = np.ones((len(ORIG_L), Z.shape[1]))
    ub[:, -1] = 2.0
    if len(sp) > 1:
        ub[:, -2] = 2.0
    prior = np.tile((sgdf.loc[idx].sum() / comp_s.sum()).values, (len(ORIG_L), 1))
    prior = 2 * prior / prior.sum(1, keepdims=True)
    P = solve(S, Z, comp_s.values, row_sum=2.0, ub=ub, prior=prior, n0=N0)
    for i, o in enumerate(ORIG_L):
        for j, g in enumerate(sgdf.columns):
            perf_sen.append(dict(uf=uf, origem=o, candidato=str(g), p=P[i, j]))
    for c in sp:
        perf_sen.append(dict(uf=uf, origem="_peso_outros", candidato=str(c), p=stot[c] / stot[sp].sum()))
    diag.append(dict(uf=uf, etapa="senado", unidades=len(idx), r2_medio=float(np.nanmean(r2(Z, S @ P, comp_s.values)[:-1]))))
    print(uf, nu, flush=True, end=" ")

print()
pd.DataFrame(fluxos).to_csv(OUT / "fluxos_por_uf.csv", index=False)
pd.DataFrame(perf_dep).to_csv(OUT / "perfis_deputado_blocos.csv", index=False)
pd.DataFrame(perf_sen).to_csv(OUT / "perfis_senado.csv", index=False)
pd.DataFrame(diag).to_csv(OUT / "diagnostico_ei.csv", index=False)
pd.DataFrame(theta_nac, index=ORIG_T, columns=DEST_T).to_csv(OUT / "fluxo_taxas_nacional.csv")
