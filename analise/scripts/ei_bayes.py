"""Adendo 1, análise B2: inferência ecológica bayesiana R×C hierárquica (taxas das unidades em escala logística,
na linha de GREINER; QUINN, 2009, com covariância diagonal).

Para cada UF e cada tabela (fluxo entre turnos e perfil de deputado por bloco), cada unidade i tem, para cada
origem r, um vetor de taxas beta_ir = softmax(m_r + s_r * z_ir, 0), com z_ir ~ Normal(0, 1), m ~ Normal(0, 2) e
s ~ MeioNormal(1); a última categoria é a referência. A distribuição de destinos da unidade é a mistura
theta_i = soma_r x_ir * beta_ir, e os votos de destino entram por um núcleo multinomial (soma de T_ic * log theta_ic).
A taxa agregada da UF é a média das taxas das unidades ponderada pelo tamanho de cada origem. Uma primeira versão,
com taxas Dirichlet e concentração com hiperpriori Gama (ROSEN et al., 2001), recuperou bem as taxas sintéticas
mas não convergiu (R-hat de 1,5 a 1,9) e foi trocada por esta antes de qualquer uso com dados reais. Os limites determinísticos de Duncan e Davis (1953)
vão para um arquivo à parte.

Saída: para cada sorteio k da posteriori, uma pasta OUT/b{k} com os mesmos arquivos que ei.py grava
(fluxos_por_uf.csv e perfis_deputado_blocos.csv, com a mesma calibração por IPF dos fluxos) e o perfil do Senado
copiado do modelo principal (o Senado fica com a regressão de Goodman nesta análise). Em OUT ficam o
diagnóstico de convergência por UF e os limites.

Uso: python3 -I scripts/ei_bayes.py MUNZONA OUT GOODMAN_N0_20 [--sorteios 200] [--por-cadeia 4000]
       [--aquecimento 2000] [--cadeias 4] [--ufs AC,AL] [--semente 2026]
As cadeias rodam com --por-cadeia sorteios cada (o diagnóstico usa todos); para o motor, a posteriori é
reduzida a --sorteios sorteios igualmente espaçados.
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]
ORIG_T = ["lula1", "flavio1", "outros1", "bn1", "abst1"]
DEST_T = ["lula2", "flavio2", "bn2", "abst2"]
ORIG_L = ["lula1", "flavio1", "outros1", "bn1"]
BLOCO = {"PL": "PL",
         "PCDOB / PT / PV": "coligacao_lula", "PSOL / REDE": "coligacao_lula", "PSB": "coligacao_lula", "PDT": "coligacao_lula",
         "NOVO": "centro_direita", "MISSÃO": "centro_direita", "PP / UNIÃO": "centro_direita", "REPUBLICANOS": "centro_direita"}
BLOCOS = ["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]


def ajusta(Xc, Tc, sorteios, aquecimento, cadeias, semente, centrada=False, alvo=0.99):
    """Xc: contagens por origem (n x R); Tc: contagens por destino (n x C). Devolve sorteios de theta agregado
    (S x R x C) e o diagnóstico (R-hat máximo, ESS mínimo, divergências)."""
    import pymc as pm
    import pytensor.tensor as pt

    Xc = np.asarray(Xc, float)
    Tc = np.asarray(Tc, float)
    N = Xc.sum(1)
    ok = (N > 0) & (Tc.sum(1) > 0)
    Xc, Tc, N = Xc[ok], Tc[ok], N[ok]
    Tc = Tc * (N / Tc.sum(1))[:, None]          # mesmas pessoas nos dois lados da tabela
    Xp = Xc / N[:, None]
    n, R = Xc.shape
    C = Tc.shape[1]
    with pm.Model():
        # taxas das unidades em escala logística. No teste sintético, a parametrização não centrada com alvo de
        # aceitação 0,99 convergiu sem divergências; a centrada teve mais de mil divergências e fica só como alternativa
        m = pm.Normal("m", 0.0, 2.0, shape=(R, C - 1))
        s = pm.HalfNormal("s", 1.0, shape=(R, C - 1))
        if centrada:
            e = pm.Normal("e", m[None], s[None], shape=(n, R, C - 1))
        else:
            z = pm.Normal("z", 0.0, 1.0, shape=(n, R, C - 1))
            e = m[None] + s[None] * z
        eta = pt.concatenate([e, pt.zeros((n, R, 1))], axis=2)
        beta = pt.special.softmax(eta, axis=2)
        th = (Xp[:, :, None] * beta).sum(1)
        pm.Potential("verossimilhanca", (Tc * pt.log(th + 1e-12)).sum())
        pm.Deterministic("theta", (Xc[:, :, None] * beta).sum(0) / Xc.sum(0)[:, None])
        tr = pm.sample(draws=sorteios, tune=aquecimento, chains=cadeias, cores=min(cadeias, 4), random_seed=semente,
                       target_accept=alvo, progressbar=False, compute_convergence_checks=False)
    th = np.asarray(tr.posterior["theta"].values)              # cadeias x sorteios x R x C
    div = int(np.asarray(tr.sample_stats["diverging"].values).sum())
    rhat = rhat_split(th)
    try:
        import arviz as az
        ess = float(np.nanmin(np.asarray(az.ess(th.reshape(th.shape[0], th.shape[1], -1)))))
    except Exception:
        ess = float("nan")
    S = th.reshape(-1, R, C)
    return S, {"rhat_max": float(np.nanmax(rhat)), "ess_min": ess, "divergencias": div, "unidades": int(n),
               "rhat_celulas": np.round(rhat, 3).tolist()}


def rhat_split(x):
    """R-hat com cadeias divididas ao meio (Gelman et al.), por célula. x: cadeias x sorteios x ..."""
    c, s = x.shape[:2]
    h = s // 2
    y = np.concatenate([x[:, :h], x[:, h:2 * h]], axis=0)
    m = y.shape[0]
    media = y.mean(1)
    B = h * media.var(0, ddof=1)
    W = y.var(1, ddof=1).mean(0)
    var = (h - 1) / h * W + B / h
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.sqrt(var / W)


def limites(Xc, Tc):
    """Limites de Duncan e Davis (Fréchet) para a contagem agregada de cada célula, somando os limites das unidades."""
    Xc = np.asarray(Xc, float)
    Tc = np.asarray(Tc, float)
    N = Xc.sum(1)
    Tc = Tc * (N / np.where(Tc.sum(1) > 0, Tc.sum(1), 1))[:, None]
    lo = np.maximum(0, Xc[:, :, None] + Tc[:, None, :] - N[:, None, None]).sum(0)
    hi = np.minimum(Xc[:, :, None], Tc[:, None, :]).sum(0)
    return lo / Xc.sum(0)[:, None], hi / Xc.sum(0)[:, None]


def ipf(seed, row_tot, col_tot, it=1000):
    M = seed.copy() + 1e-9
    col_tot = col_tot * row_tot.sum() / col_tot.sum()
    for _ in range(it):
        M *= (row_tot / M.sum(1))[:, None]
        M *= (col_tot / M.sum(0))[None, :]
    return M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("munzona", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("goodman", type=Path)
    ap.add_argument("--sorteios", type=int, default=200)
    ap.add_argument("--por-cadeia", type=int, default=4000)
    ap.add_argument("--aquecimento", type=int, default=2000)
    ap.add_argument("--cadeias", type=int, default=4)
    ap.add_argument("--ufs", default="")
    ap.add_argument("--semente", type=int, default=2026)
    a = ap.parse_args()
    mz, out = a.munzona, a.out
    out.mkdir(parents=True, exist_ok=True)
    pres = pd.read_csv(mz / "pres_munzona.csv")
    dep = pd.read_csv(mz / "dep_munzona.csv")
    ldet = pd.read_csv(mz / "legis_detalhe_munzona.csv")
    dep["bloco"] = dep.agremiacao.map(BLOCO).fillna("centro_demais")
    ufs = a.ufs.split(",") if a.ufs else sorted(pres.SG_UF.unique())
    por = a.por_cadeia

    def reduz(S):
        return S[np.linspace(0, len(S) - 1, a.sorteios).round().astype(int)]
    fl, pdp, diag, lim = [], [], [], []
    for uf in ufs:
        u = pres[pres.SG_UF == uf].set_index(KEY).sort_index()
        # fluxo entre turnos
        Xc = u[ORIG_T].values
        Tc = u[DEST_T].values
        S, dg = ajusta(Xc, Tc, por, a.aquecimento, a.cadeias, a.semente)
        S = reduz(S)
        diag.append({"uf": uf, "tabela": "fluxo", **dg})
        lo, hi = limites(Xc, Tc)
        lim += [{"uf": uf, "tabela": "fluxo", "origem": o, "destino": d, "min": lo[i, j], "max": hi[i, j]}
                for i, o in enumerate(ORIG_T) for j, d in enumerate(DEST_T)]
        rt, ct = u[ORIG_T].sum().values.astype(float), u[DEST_T].sum().values.astype(float)
        for k in range(S.shape[0]):
            F = ipf(rt[:, None] * S[k], rt, ct)
            fl += [{"b": k, "uf": uf, "origem": o, "destino": d, "taxa_ei": S[k, i, j], "votos": F[i, j]}
                   for i, o in enumerate(ORIG_T) for j, d in enumerate(DEST_T)]
        # perfil de deputado por bloco
        lc = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].set_index(KEY)
        dd = dep[dep.SG_UF == uf].pivot_table(index=KEY, columns="bloco", values="votos", aggfunc="sum", fill_value=0)
        dd["_branco_nulo"] = lc.bn
        dd = dd.reindex(columns=BLOCOS, fill_value=0)
        idx = u.index.intersection(dd.index).intersection(lc.index)
        Xl = u.loc[idx, ORIG_L].values.astype(float)
        Tl = dd.loc[idx].values.astype(float)
        S, dg = ajusta(Xl, Tl, por, a.aquecimento, a.cadeias, a.semente + 1)
        S = reduz(S)
        diag.append({"uf": uf, "tabela": "deputado_blocos", **dg})
        lo, hi = limites(Xl, Tl)
        lim += [{"uf": uf, "tabela": "deputado_blocos", "origem": o, "destino": g, "min": lo[i, j], "max": hi[i, j]}
                for i, o in enumerate(ORIG_L) for j, g in enumerate(BLOCOS)]
        for k in range(S.shape[0]):
            pdp += [{"b": k, "uf": uf, "origem": o, "bloco": g, "p": S[k, i, j]}
                    for i, o in enumerate(ORIG_L) for j, g in enumerate(BLOCOS)]
        print(uf, diag[-2]["rhat_max"].__round__(3), diag[-1]["rhat_max"].__round__(3), flush=True)
    fl, pdp = pd.DataFrame(fl), pd.DataFrame(pdp)
    for k in range(a.sorteios):
        ok = out / f"b{k}"
        ok.mkdir(exist_ok=True)
        fl[fl.b == k].drop(columns="b").to_csv(ok / "fluxos_por_uf.csv", index=False)
        pdp[pdp.b == k].drop(columns="b").to_csv(ok / "perfis_deputado_blocos.csv", index=False)
        shutil.copy(a.goodman / "perfis_senado.csv", ok / "perfis_senado.csv")
    pd.DataFrame(diag).to_csv(out / "diagnostico_bayes.csv", index=False)
    pd.DataFrame(lim).to_csv(out / "limites_duncan_davis.csv", index=False)


if __name__ == "__main__":
    main()
