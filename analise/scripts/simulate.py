"""Simulação: aplica no 1º turno (Senado e Câmara) a variação de Lula entre o 1º e o 2º turno.

Swing por UF = participação de Lula no voto bipartidário (Lula / (Lula + Flávio)) no 2º turno
menos a mesma medida no 1º turno. Esse swing é aplicado à divisão de votos entre o campo de
Lula e o campo de Flávio no Legislativo: transfere-se T = swing * (votos L + votos F) do campo F
para o campo L, proporcionalmente aos votos de cada candidato/agremiação. O resto fica igual.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seats import distribuir  # noqa: E402

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

L_PARTIDOS = {"PT", "PCDOB", "PV", "PSB", "PDT", "PSOL", "REDE"}  # coligação de Lula no 1º turno
F_RESTRITO = {"PL"}                                                # coligação de Flávio no 1º turno
F_AMPLO = F_RESTRITO | {"NOVO", "MISSÃO", "PP", "UNIÃO", "REPUBLICANOS"}


def tokens(com):
    return {t.strip().strip("*").strip() for t in str(com).split("/") if t.strip()}


# ---------------- swing por UF ----------------
pres = pd.read_csv(DATA / "presidente_por_uf_1t_2t.csv", keep_default_na=False)
pv = pres[pres.candidato.isin(["LULA", "FLAVIO BOLSONARO"])].pivot_table(
    index=["uf"], columns=["turno", "candidato"], values="votos", aggfunc="sum")
sw = pd.DataFrame(index=pv.index)
sw["lula_1t"] = pv[(1, "LULA")]
sw["flavio_1t"] = pv[(1, "FLAVIO BOLSONARO")]
sw["lula_2t"] = pv[(2, "LULA")]
sw["flavio_2t"] = pv[(2, "FLAVIO BOLSONARO")]
sw["share_lula_1t"] = sw.lula_1t / (sw.lula_1t + sw.flavio_1t)
sw["share_lula_2t"] = sw.lula_2t / (sw.lula_2t + sw.flavio_2t)
sw["swing"] = sw.share_lula_2t - sw.share_lula_1t
SWING_NACIONAL = float(sw.loc["BR", "swing"])
sw.to_csv(OUT / "swing_por_uf.csv")


def transferir(df, campo_col, votos_col, delta):
    """Transfere votos de F para L numa UF. Retorna nova série de votos."""
    L = df.loc[df[campo_col] == "L", votos_col].sum()
    F = df.loc[df[campo_col] == "F", votos_col].sum()
    novo = df[votos_col].astype(float).copy()
    if L == 0 or F == 0 or delta == 0:
        return novo
    T = delta * (L + F)
    T = max(min(T, F), -L)  # não deixa voto negativo
    novo[df[campo_col] == "F"] -= T * df.loc[df[campo_col] == "F", votos_col] / F
    novo[df[campo_col] == "L"] += T * df.loc[df[campo_col] == "L", votos_col] / L
    return novo


# ---------------- Senado ----------------
sen = pd.read_csv(DATA / "senado_candidatos_2026.csv", keep_default_na=False)
sen = sen[sen.destino_voto.str.startswith("Válido")].copy()


def campo_senado(r, f_set):
    com = tokens(r.composicao_coligacao)
    if r.partido in L_PARTIDOS:
        return "L"
    if r.partido == "PL":
        return "F"
    if "PT" in com:
        return "L"
    if "PL" in com:
        return "F"
    if r.partido in f_set:
        return "F"
    return "N"


cenarios = {
    "restrito_uf": (F_RESTRITO, "uf"),
    "amplo_uf": (F_AMPLO, "uf"),
    "restrito_nacional": (F_RESTRITO, "nacional"),
}

sen_res = []
for nome, (fset, modo) in cenarios.items():
    sen[f"campo_{nome}"] = sen.apply(campo_senado, axis=1, f_set=fset)
    for uf, g in sen.groupby("uf"):
        delta = sw.loc[uf, "swing"] if modo == "uf" else SWING_NACIONAL
        novos = transferir(g, f"campo_{nome}", "votos", delta)
        vagas = int(g.vagas.iloc[0])
        top = novos.sort_values(ascending=False).index[:vagas]
        sen.loc[g.index, f"votos_{nome}"] = novos.round().astype(int)
        sen.loc[g.index, f"eleito_{nome}"] = g.index.isin(top)

sen.to_csv(OUT / "senado_simulacao.csv", index=False)

# ---------------- Câmara ----------------
p = pd.read_csv(DATA / "camara_partidos_2026.csv", keep_default_na=False)
c = pd.read_csv(DATA / "camara_candidatos_2026.csv", keep_default_na=False)
c = c[c.destino_voto.str.startswith("Válido")].copy()
p["votos"] = p.votos_total + p.votos_legenda
agr = p.groupby(["uf", "agremiacao"], as_index=False).agg(
    votos=("votos", "sum"), vagas_oficial=("vagas_agr_oficial", "first"),
    vagas_uf=("vagas_uf", "first"), vv=("votos_validos_uf", "first"))


def campo_agr(ag, fset):
    t = tokens(ag)
    if t & L_PARTIDOS and not t & fset:
        return "L"
    if t & fset and not t & L_PARTIDOS:
        return "F"
    return "N"


cam_rows = []
eleitos_sim = []
for nome, (fset, modo) in cenarios.items():
    agr[f"campo_{nome}"] = agr.agremiacao.apply(campo_agr, fset=fset)
    for uf, g in agr.groupby("uf"):
        delta = sw.loc[uf, "swing"] if modo == "uf" else SWING_NACIONAL
        novos = transferir(g, f"campo_{nome}", "votos", delta)
        fatores = (novos / g.votos).to_dict()
        agrs = {}
        for idx, r in g.iterrows():
            cv = c[(c.uf == uf) & (c.agremiacao == r.agremiacao)].votos * fatores[idx]
            agrs[r.agremiacao] = {"votos": int(round(novos[idx])), "cands": cv.tolist()}
        res, _ = distribuir(agrs, int(g.vagas_uf.iloc[0]), int(g.vv.iloc[0]))
        for idx, r in g.iterrows():
            agr.loc[idx, f"votos_{nome}"] = int(round(novos[idx]))
            agr.loc[idx, f"vagas_{nome}"] = res[r.agremiacao]
            # eleitos: os k mais votados da agremiação (escala uniforme preserva a ordem)
            cc = c[(c.uf == uf) & (c.agremiacao == r.agremiacao)].sort_values("votos", ascending=False)
            for _, cr in cc.head(res[r.agremiacao]).iterrows():
                eleitos_sim.append(dict(cenario=nome, uf=uf, agremiacao=r.agremiacao,
                                        partido=cr.partido, candidato=cr.candidato, votos_reais=cr.votos))

agr.to_csv(OUT / "camara_simulacao_agremiacoes.csv", index=False)
el = pd.DataFrame(eleitos_sim)
el.to_csv(OUT / "camara_simulacao_eleitos.csv", index=False)

# ---------------- Resumos ----------------
print(f"Swing nacional (bipartidário): {SWING_NACIONAL*100:+.2f} p.p.")
print(sw[["share_lula_1t", "share_lula_2t", "swing"]].mul(100).round(2).sort_values("swing").to_string())

real_cam = c[c.eleito].partido.value_counts()
tab = pd.DataFrame({"real": real_cam})
for nome in cenarios:
    tab[nome] = el[el.cenario == nome].partido.value_counts()
tab = tab.fillna(0).astype(int)
tab["dif_restrito_uf"] = tab.restrito_uf - tab.real
tab["dif_amplo_uf"] = tab.amplo_uf - tab.real
tab = tab.sort_values("real", ascending=False)
tab.to_csv(OUT / "camara_bancadas_real_vs_simulado.csv")
print("\nCÂMARA - bancadas por partido"); print(tab.to_string())

print("\nSENADO - cadeiras que mudariam de dono")
for nome in cenarios:
    print(f"== {nome}")
    for uf, g in sen.groupby("uf"):
        sai = g[g.eleito & ~g[f"eleito_{nome}"]]
        entra = g[~g.eleito & g[f"eleito_{nome}"]]
        for (_, a), (_, b) in zip(sai.iterrows(), entra.iterrows()):
            print(f"  {uf}: sai {a.candidato} ({a.partido}) -> entra {b.candidato} ({b.partido})"
                  f"  | swing {sw.loc[uf,'swing']*100:+.1f}")
    real = sen[sen.eleito].partido.value_counts()
    simu = sen[sen[f"eleito_{nome}"]].partido.value_counts()
    d = (simu.reindex(real.index.union(simu.index)).fillna(0) - real.reindex(real.index.union(simu.index)).fillna(0))
    print("  saldo:", {k: int(v) for k, v in d.items() if v})
