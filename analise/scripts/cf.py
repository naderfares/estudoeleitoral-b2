"""Contrafactual revisado: o eleitorado do 2º turno votando no 1º turno.

Para cada fluxo de eleitores entre turnos (estimado em ei.py), decide se o voto legislativo muda:
  Cenário A (principal)
    - quem se absteve no 1º e votou no 2º passa a votar também para o Legislativo, com o perfil
      dos eleitores do candidato que escolheu (Lula, Flávio ou branco/nulo) naquela UF;
    - quem votou no 1º e se absteve no 2º sai do Legislativo (perde o perfil da sua categoria);
    - quem trocou Flávio <-> Lula troca o perfil legislativo de um pelo do outro;
    - eleitores dos outros presidenciáveis e de branco/nulo que escolheram Lula ou Flávio no 2º turno
      MANTÊM o voto legislativo que deram de fato.
  Cenário B (teto, arrasto total): como A, mas todo eleitor que mudou de categoria entre os turnos
      adota o perfil legislativo da sua escolha no 2º turno.
Perfis calibrados para reproduzir exatamente os votos reais de cada UF.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seats import distribuir  # noqa: E402

R2 = Path(sys.argv[1])
DATA = Path(sys.argv[2])
MZ = Path(sys.argv[3])
ORIG = ["lula1", "flavio1", "outros1", "bn1"]
PERFIL_DESTINO = {"lula2": "lula1", "flavio2": "flavio1", "bn2": "bn1"}
BLOCO = {"PL": "PL", "PCDOB / PT / PV": "coligacao_lula", "PSOL / REDE": "coligacao_lula", "PSB": "coligacao_lula",
         "PDT": "coligacao_lula", "NOVO": "centro_direita", "MISSÃO": "centro_direita", "PP / UNIÃO": "centro_direita",
         "REPUBLICANOS": "centro_direita"}

fl = pd.read_csv(R2 / "fluxos_por_uf.csv")
pdp = pd.read_csv(R2 / "perfis_deputado_blocos.csv")
psn = pd.read_csv(R2 / "perfis_senado.csv", dtype={"candidato": str})
pres = pd.read_csv(MZ / "pres_munzona.csv")
dep = pd.read_csv(MZ / "dep_munzona.csv")
sen = pd.read_csv(MZ / "sen_munzona.csv")
ldet = pd.read_csv(MZ / "legis_detalhe_munzona.csv")


def ipf(seed, row_tot, col_tot, it=1000):
    M = seed.copy() + 1e-9
    col_tot = col_tot * row_tot.sum() / col_tot.sum()
    for _ in range(it):
        M *= (row_tot / M.sum(1))[:, None]
        M *= (col_tot / M.sum(0))[None, :]
    return M


def delta(n, P, cenario, avg=None):
    """Variação do voto legislativo. n: (origem,destino)->eleitores; P: origem x grupo (por eleitor).
    A     : quem passou a votar no 2º turno entra com o perfil da sua escolha; troca direta Lula<->Flávio
            troca de perfil; todos os eleitores do 1º turno mantêm o voto legislativo real.
    A_liq : A + quem votou no 1º e faltou no 2º sai (variante de sensibilidade).
    B     : A + eleitores de outros presidenciáveis que escolheram Lula ou Flávio no 2º turno adotam o
            perfil legislativo dessa escolha (teto). Como o perfil real desses eleitores não é estimável
            com confiança, assume-se que votavam como a média da UF (avg). Branco/nulo do 1º turno fica fora
            (parte é erro na urna de 6 cargos, que continuaria existindo no 1º turno)."""
    d = pd.Series(0.0, index=P.columns)
    for dest, perf in PERFIL_DESTINO.items():
        d += n[("abst1", dest)] * P.loc[perf]
    d += n[("flavio1", "lula2")] * (P.loc["lula1"] - P.loc["flavio1"])
    d += n[("lula1", "flavio2")] * (P.loc["flavio1"] - P.loc["lula1"])
    if cenario == "A_liq":
        for o in ORIG:
            d -= n[(o, "abst2")] * P.loc[o]
    if cenario == "B":
        for dest in ("lula2", "flavio2"):
            d += n[("outros1", dest)] * (P.loc[PERFIL_DESTINO[dest]] - avg)
    return d


CENARIOS = ("A", "A_liq", "B")
cam_out, sen_out, cam_eleitos, perfis_cal = [], [], [], []
cp_api = pd.read_csv(DATA / "camara_partidos_2026.csv", keep_default_na=False)
cc_api = pd.read_csv(DATA / "camara_candidatos_2026.csv", keep_default_na=False)
cc_api = cc_api[cc_api.destino_voto.str.startswith("Válido")]
sen_api = pd.read_csv(DATA / "senado_candidatos_2026.csv", keep_default_na=False)
sen_api = sen_api[sen_api.destino_voto.str.startswith("Válido")]

for uf in sorted(fl.uf.unique()):
    f = fl[fl.uf == uf]
    n = {(r.origem, r.destino): r.votos for r in f.itertuples()}
    # eleitores do 1º turno por categoria (comparecimento presidencial, sem trânsito)
    u = pres[pres.SG_UF == uf]
    rows = np.array([u.lula1.sum(), u.flavio1.sum(), u.outros1.sum(), u.bn1.sum()], dtype=float)

    # ---------------- Câmara (perfil por bloco) ----------------
    pp = pdp[(pdp.uf == uf)].pivot(index="origem", columns="bloco", values="p").loc[ORIG]
    d_uf = dep[dep.SG_UF == uf].groupby("agremiacao").votos.sum()
    bloco_de = {a: BLOCO.get(a, "centro_demais") for a in d_uf.index}
    bn_dep = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].bn.sum()
    col_real = pd.Series({b: (bn_dep if b == "_branco_nulo" else d_uf[[a for a in d_uf.index if bloco_de[a] == b]].sum())
                          for b in pp.columns})
    M = ipf(pp.values * rows[:, None], rows, col_real.values.astype(float))
    P = pd.DataFrame(M / rows[:, None], index=ORIG, columns=pp.columns)
    perfis_cal.append(P.assign(uf=uf, cargo="deputado"))
    g_api = cp_api[cp_api.uf == uf].assign(v=lambda x: x.votos_total + x.votos_legenda).groupby("agremiacao").agg(
        v=("v", "sum"), vagas=("vagas_agr_oficial", "first"), vagas_uf=("vagas_uf", "first"))
    for cen in CENARIOS:
        dg = delta(n, P, cen, avg=(P.mul(rows, axis=0).sum() / rows.sum()))
        dv = {}
        for ag in g_api.index:
            b = BLOCO.get(ag, "centro_demais")
            tot_b = col_real[b]
            dv[ag] = dg[b] * (g_api.loc[ag, "v"] / tot_b) if tot_b else 0.0
        agrs, fatores = {}, {}
        for ag, r in g_api.iterrows():
            novo = max(r.v + dv.get(ag, 0.0), 0.0)
            fatores[ag] = novo / r.v if r.v else 1.0
            cands = (cc_api[(cc_api.uf == uf) & (cc_api.agremiacao == ag)].votos * fatores[ag]).tolist()
            agrs[ag] = {"votos": int(round(novo)), "cands": cands}
        vv = sum(a["votos"] for a in agrs.values())
        res, qe = distribuir(agrs, int(g_api.vagas_uf.iloc[0]), vv)
        for ag, r in g_api.iterrows():
            cam_out.append(dict(cenario=cen, uf=uf, agremiacao=ag, bloco=BLOCO.get(ag, "centro_demais"),
                                votos_real=int(r.v), votos_sim=agrs[ag]["votos"],
                                vagas_real=int(r.vagas), vagas_sim=res[ag], qe_sim=qe))
            top = cc_api[(cc_api.uf == uf) & (cc_api.agremiacao == ag)].sort_values("votos", ascending=False).head(res[ag])
            for _, c in top.iterrows():
                cam_eleitos.append(dict(cenario=cen, uf=uf, partido=c.partido, candidato=c.candidato))

    # ---------------- Senado ----------------
    ps = psn[(psn.uf == uf) & (psn.origem.isin(ORIG))].pivot(index="origem", columns="candidato", values="p").loc[ORIG]
    peso_s = psn[(psn.uf == uf) & (psn.origem == "_peso_outros")].set_index("candidato").p
    sreal = sen[sen.SG_UF == uf].groupby("NR_CANDIDATO").votos.sum()
    sreal.index = sreal.index.astype(str)
    bn_sen = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 5)].bn.sum()
    col_s = pd.Series({g: (sreal[peso_s.index].sum() if g == "_outros" else bn_sen if g == "_branco_nulo" else sreal[g])
                       for g in ps.columns})
    Ms = ipf(ps.values * 2 * rows[:, None], 2 * rows, col_s.values.astype(float))
    Psen = pd.DataFrame(Ms / rows[:, None], index=ORIG, columns=ps.columns)
    perfis_cal.append(Psen.assign(uf=uf, cargo="senado"))
    sa = sen_api[sen_api.uf == uf].copy()
    sa["numero"] = sa.numero.astype(str)
    for cen in CENARIOS:
        ds = delta(n, Psen, cen, avg=(Psen.mul(rows, axis=0).sum() / rows.sum()))
        dvs = {c: ds[c] for c in ps.columns if c not in ("_outros", "_branco_nulo")}
        for c, w in peso_s.items():
            dvs[c] = ds.get("_outros", 0.0) * w
        sa[f"votos_{cen}"] = [v + dvs.get(num, 0.0) for v, num in zip(sa.votos, sa.numero)]
        top = sa.sort_values(f"votos_{cen}", ascending=False).index[:2]
        sa[f"eleito_{cen}"] = sa.index.isin(top)
    sen_out.append(sa)

cam = pd.DataFrame(cam_out)
el = pd.DataFrame(cam_eleitos)
sres = pd.concat(sen_out)
cam.to_csv(R2 / "camara_cf_agremiacoes.csv", index=False)
el.to_csv(R2 / "camara_cf_eleitos.csv", index=False)
sres.to_csv(R2 / "senado_cf.csv", index=False)
pd.concat(perfis_cal).to_csv(R2 / "perfis_calibrados.csv")

# ---------------- resumo ----------------
real = cc_api[cc_api.eleito.astype(str) == "True"].partido.value_counts()
tab = pd.DataFrame({"real": real, **{c: el[el.cenario == c].partido.value_counts() for c in CENARIOS}}).fillna(0).astype(int)
old = pd.read_csv(Path(sys.argv[4]) / "camara_bancadas_real_vs_simulado.csv", index_col=0)
tab["modelo_antigo_restrito"] = old.restrito_uf
tab = tab.fillna(0).astype(int).sort_values("real", ascending=False)
tab.to_csv(R2 / "camara_cf_bancadas.csv")
print(tab.to_string())
L = ["PT", "PCDOB", "PV", "PSB", "PDT", "PSOL", "REDE"]
print("\nColigação Lula:", tab.loc[tab.index.isin(L)].sum().to_dict())
print("Mudanças por UF (A):")
mud = cam[(cam.cenario == "A") & (cam.vagas_sim != cam.vagas_real)]
print(mud[["uf", "agremiacao", "votos_real", "votos_sim", "vagas_real", "vagas_sim"]].to_string(index=False))
print("Mudanças por UF (B):")
mud = cam[(cam.cenario == "B") & (cam.vagas_sim != cam.vagas_real)]
print(mud[["uf", "agremiacao", "votos_real", "votos_sim", "vagas_real", "vagas_sim"]].to_string(index=False))
for cen in CENARIOS:
    print(f"\nSENADO {cen}:")
    for uf, g in sres.groupby("uf"):
        sai = g[(g.eleito.astype(str) == "True") & ~g[f"eleito_{cen}"]]
        ent = g[(g.eleito.astype(str) != "True") & g[f"eleito_{cen}"]]
        for (_, a), (_, b) in zip(sai.iterrows(), ent.iterrows()):
            print(f"  {uf}: sai {a.candidato} ({a.partido}) -> entra {b.candidato} ({b.partido})")
