"""Motor parametrizado: testa comportamentos possíveis de cada grupo de eleitores que mudou entre turnos.

Parâmetros (caso-base = cenário A da versão 2):
  alpha_L  inclinação do voto legislativo dos NOVOS eleitores de Lula (abstenção 1T -> Lula 2T):
           -1 = votam como o eleitor médio da UF (sem viés de esquerda); 0 = como o eleitor típico de Lula
           da UF; +1 = todo voto válido na coligação de Lula ("militância máxima")
  rho      roll-off: fração dos novos eleitores que vai só para votar em presidente (branco no Legislativo)
  alpha_F  idem para novos eleitores de Flávio (+1 = todo voto válido no PL / campo de Flávio)
  geo      1 = perfil dos novos eleitores ajustado à geografia da mobilização (vizinhos de mesma escolha)
  lam_O    arrasto sobre eleitores dos outros presidenciáveis que escolheram Lula/Flávio (0 = mantêm voto real)
  lam_BN   fração dos eleitores branco/nulo do 1T que foram a Lula/Flávio e mudariam o voto legislativo
  mu       fração do fluxo branco/nulo 1T -> Lula reclassificada como abstenção 1T -> Lula (mais mobilização)
  demob    1 = quem votou no 1T e faltou no 2T perde o voto legislativo
  lam_S    fração do efeito para quem trocou Flávio <-> Lula
  kappa    fração do ganho do bloco da coligação de Lula que vai só para a federação PT/PCdoB/PV
  nu       fração do fluxo outros presidenciáveis -> Lula reclassificada como abstenção -> Lula
  tau_L    "efeito clima": fração do voto dos eleitores FIÉIS de Lula em partidos/candidatos de centro que
           migraria para o campo de Lula se a polarização do 2º turno tivesse ocorrido antes do 1º
  tau_F    idem para eleitores fiéis de Flávio (migram para o PL/campo de Flávio)
  n0       âncora estatística da inferência ecológica (0, 20, 100)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seats import distribuir  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/Users/nader/workspace/personal/estudoeleitoral/analise")
DATA, MZ = ROOT / "data", ROOT / "munzona"
BLOCO = {"PL": "PL", "PCDOB / PT / PV": "coligacao_lula", "PSOL / REDE": "coligacao_lula", "PSB": "coligacao_lula",
         "PDT": "coligacao_lula", "NOVO": "centro_direita", "MISSÃO": "centro_direita", "PP / UNIÃO": "centro_direita",
         "REPUBLICANOS": "centro_direita"}
BL = ["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]
IPL, ICL, IBN = 0, 1, 4
ORIG = ["lula1", "flavio1", "outros1", "bn1"]
L_PART = {"PT", "PCDOB", "PV", "PSB", "PDT", "PSOL", "REDE"}
KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]
BASE = dict(alpha_L=0.0, rho=0.0, alpha_F=0.0, geo=0, lam_O=0.0, lam_BN=0.0, mu=0.0, nu=0.0, demob=0, lam_S=1.0,
            kappa=0.0, tau_L=0.0, tau_F=0.0, n0=20)

# ---------------- dados estáticos ----------------
cp_api = pd.read_csv(DATA / "camara_partidos_2026.csv", keep_default_na=False)
cc_api = pd.read_csv(DATA / "camara_candidatos_2026.csv", keep_default_na=False)
cc_api = cc_api[cc_api.destino_voto.str.startswith("Válido")]
sen_api = pd.read_csv(DATA / "senado_candidatos_2026.csv", keep_default_na=False)
sen_api = sen_api[sen_api.destino_voto.str.startswith("Válido")]
v1 = pd.read_csv(ROOT / "results" / "senado_simulacao.csv", keep_default_na=False)
campo_sen = {(r.uf, str(r.numero)): r.campo_restrito_uf for r in v1.itertuples()}
pres = pd.read_csv(MZ / "pres_munzona.csv")
dep = pd.read_csv(MZ / "dep_munzona.csv")
dep["bloco"] = dep.agremiacao.map(BLOCO).fillna("centro_demais")
senmz = pd.read_csv(MZ / "sen_munzona.csv")
ldet = pd.read_csv(MZ / "legis_detalhe_munzona.csv")

UFS = sorted(pres.SG_UF.unique())
ST = {}
for uf in UFS:
    s = {}
    u = pres[pres.SG_UF == uf].set_index(KEY)
    s["rows"] = np.array([u.lula1.sum(), u.flavio1.sum(), u.outros1.sum(), u.bn1.sum()], float)
    g = cp_api[cp_api.uf == uf].assign(v=lambda x: x.votos_total + x.votos_legenda).groupby("agremiacao").agg(
        v=("v", "sum"), vagas=("vagas_agr_oficial", "first"), vagas_uf=("vagas_uf", "first"))
    s["agr"] = list(g.index)
    s["agr_v"] = g.v.values.astype(float)
    s["agr_b"] = np.array([BL.index(BLOCO.get(a, "centro_demais")) for a in g.index])
    s["vagas_uf"] = int(g.vagas_uf.iloc[0])
    cands, parts = [], []
    for a in g.index:
        cc = cc_api[(cc_api.uf == uf) & (cc_api.agremiacao == a)].sort_values("votos", ascending=False)
        cands.append(cc.votos.values.astype(float))
        parts.append(cc.partido.values)
    s["cands"], s["parts"] = cands, parts
    bn_dep = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].bn.sum()
    colb = np.array([s["agr_v"][s["agr_b"] == i].sum() for i in range(4)] + [bn_dep], float)
    s["bloc_tot"] = colb
    s["avg_dep"] = colb / colb.sum()
    # senado
    sa = sen_api[sen_api.uf == uf]
    s["sen_num"] = [str(x) for x in sa.numero]
    s["sen_nome"] = [f"{a} ({b})" for a, b in zip(sa.candidato, sa.partido)]
    s["sen_v"] = sa.votos.values.astype(float)
    s["sen_campo"] = np.array([campo_sen.get((uf, n), "N") for n in s["sen_num"]])
    s["sen_eleito"] = np.array([str(x) == "True" for x in sa.eleito])
    # unidades para perfil geográfico
    s["units"] = u
    ST[uf] = s


def load_model(n0):
    R = ROOT / f"results2_n0_{n0}"
    fl = pd.read_csv(R / "fluxos_por_uf.csv")
    pc = pd.read_csv(R / "perfis_calibrados.csv", index_col=0)
    psn = pd.read_csv(R / "perfis_senado.csv", dtype={"candidato": str})
    M = {}
    for uf in UFS:
        m = {}
        f = fl[fl.uf == uf]
        m["n"] = {(r.origem, r.destino): r.votos for r in f.itertuples()}
        P = pc[(pc.uf == uf) & (pc.cargo == "deputado")][BL].loc[ORIG].values
        m["P"] = P
        ps = pc[(pc.uf == uf) & (pc.cargo == "senado")].drop(columns=["uf", "cargo"]).dropna(axis=1, how="all").loc[ORIG]
        m["scols"] = list(ps.columns)
        m["Ps"] = ps.values
        peso = psn[(psn.uf == uf) & (psn.origem == "_peso_outros")].set_index("candidato").p.to_dict()
        s = ST[uf]
        # matriz de expansão colunas do perfil -> candidatos
        E = np.zeros((len(m["scols"]), len(s["sen_num"])))
        for i, c in enumerate(m["scols"]):
            if c == "_branco_nulo":
                continue
            if c == "_outros":
                for j, num in enumerate(s["sen_num"]):
                    E[i, j] = peso.get(num, 0.0)
            elif c in s["sen_num"]:
                E[i, s["sen_num"].index(c)] = 1.0
        m["E"] = E
        rows = s["rows"]
        m["avg_s"] = (m["Ps"] * rows[:, None]).sum(0) / rows.sum()
        m["ibn_s"] = m["scols"].index("_branco_nulo")
        # campo de cada coluna do senado (para perfis militantes)
        m["scampo"] = np.array([s["sen_campo"][s["sen_num"].index(c)] if c in s["sen_num"] else "N" for c in m["scols"]])
        m["sv_col"] = np.array([s["sen_v"][s["sen_num"].index(c)] if c in s["sen_num"] else 0.0 for c in m["scols"]])
        # perfis geográficos dos novos eleitores
        m["geo_L"], m["geo_F"], m["geo_Ls"], m["geo_Fs"] = geo_profiles(uf, m)
        M[uf] = m
    return M


def geo_profiles(uf, m):
    """Novos eleitores votam como os vizinhos de mesma escolha: perfil da UF ajustado pela força local
    de cada bloco/candidato, ponderado por onde o comparecimento cresceu."""
    s = ST[uf]
    u = s["units"]
    mob = (u.comp2 - u.comp1).clip(lower=0)
    wl = mob * u.lula2 / (u.lula2 + u.flavio2)
    wf = mob * u.flavio2 / (u.lula2 + u.flavio2)
    d = dep[dep.SG_UF == uf].pivot_table(index=KEY, columns="bloco", values="votos", aggfunc="sum", fill_value=0)
    lc = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].set_index(KEY)
    d["_branco_nulo"] = lc.bn
    d = d.reindex(columns=BL, fill_value=0).reindex(u.index).fillna(0)
    sh = d.div(d.sum(1).replace(0, np.nan), axis=0).fillna(0).values
    rel = sh / np.where(s["avg_dep"] > 0, s["avg_dep"], 1)

    def adj(p, rel, w):
        A = p[None, :] * rel
        A = A / np.where(A.sum(1, keepdims=True) > 0, A.sum(1, keepdims=True), 1)
        if w.sum() <= 0:
            return p
        return (A * w.values[:, None]).sum(0) / w.sum()

    gL, gF = adj(m["P"][0], rel, wl), adj(m["P"][1], rel, wf)
    # senado
    sv = senmz[senmz.SG_UF == uf].pivot_table(index=KEY, columns="NR_CANDIDATO", values="votos", aggfunc="sum", fill_value=0)
    sv.columns = sv.columns.astype(str)
    ls = ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 5)].set_index(KEY)
    cols = []
    for c in m["scols"]:
        if c == "_branco_nulo":
            cols.append(ls.bn.reindex(u.index).fillna(0))
        elif c == "_outros":
            small = [x for x in sv.columns if x not in m["scols"]]
            cols.append(sv[small].sum(1).reindex(u.index).fillna(0))
        else:
            cols.append(sv[c].reindex(u.index).fillna(0))
    Sv = np.vstack([c.values for c in cols]).T
    shs = 2 * Sv / np.where(Sv.sum(1, keepdims=True) > 0, Sv.sum(1, keepdims=True), 1)
    rels = shs / np.where(m["avg_s"] > 0, m["avg_s"], 1)

    def adj_s(p, w):
        A = p[None, :] * rels
        A = 2 * A / np.where(A.sum(1, keepdims=True) > 0, A.sum(1, keepdims=True), 1)
        if w.sum() <= 0:
            return p
        q = (A * w.values[:, None]).sum(0) / w.sum()
        return cap_senado(q, m["ibn_s"])

    return gL, gF, adj_s(m["Ps"][0], wl), adj_s(m["Ps"][1], wf)


def cap_senado(q, ibn):
    q = q.copy()
    for _ in range(20):
        over = (q > 1) & (np.arange(len(q)) != ibn)
        if not over.any():
            break
        excess = (q[over] - 1).sum()
        q[over] = 1
        q[ibn] += excess
    return q


def militante_dep(b, alvo):
    m = np.zeros_like(b)
    m[IBN] = b[IBN]
    m[alvo] = 1 - b[IBN]
    return m


def militante_sen(b, m, campo):
    q = np.zeros_like(b)
    ibn = m["ibn_s"]
    q[ibn] = b[ibn]
    R = 2 - b[ibn]
    idx = np.where(m["scampo"] == campo)[0]
    if len(idx) == 0:
        q[ibn] += R
        return q
    w = m["sv_col"][idx] / m["sv_col"][idx].sum()
    q[idx] = R * w
    return cap_senado(q, ibn)


def tilt(b, alpha, avg, mil):
    return (1 - alpha) * b + alpha * mil if alpha >= 0 else (1 + alpha) * b + (-alpha) * avg


def run(par, M):
    p = {**BASE, **par}
    out = {"PL": 0, "PT": 0, "colig": 0, "outros": 0, "sen_L": 0, "sen_F": 0, "sen_N": 0}
    flips = []
    margens = {}
    for uf in UFS:
        s, m = ST[uf], M[uf]
        n = dict(m["n"])
        x = p["mu"] * n[("bn1", "lula2")]
        n[("bn1", "lula2")] -= x
        n[("abst1", "lula2")] += x
        y = p["nu"] * n[("outros1", "lula2")]
        n[("outros1", "lula2")] -= y
        n[("abst1", "lula2")] += y
        for cargo in ("dep", "sen"):
            if cargo == "dep":
                P, avg = m["P"], s["avg_dep"]
                eBN = np.eye(len(BL))[IBN]
                bL = m["geo_L"] if p["geo"] else P[0]
                bF = m["geo_F"] if p["geo"] else P[1]
                milL, milF = militante_dep(bL, ICL), militante_dep(bF, IPL)
                pbn = 0.6 * eBN + 0.4 * avg
            else:
                P, avg = m["Ps"], m["avg_s"]
                eBN = np.zeros(P.shape[1])
                eBN[m["ibn_s"]] = 2.0
                bL = m["geo_Ls"] if p["geo"] else P[0]
                bF = m["geo_Fs"] if p["geo"] else P[1]
                milL, milF = militante_sen(bL, m, "L"), militante_sen(bF, m, "F")
                pbn = 0.6 * eBN + 0.4 * avg
            qL = (1 - p["rho"]) * tilt(bL, p["alpha_L"], avg, milL) + p["rho"] * eBN
            qF = (1 - p["rho"]) * tilt(bF, p["alpha_F"], avg, milF) + p["rho"] * eBN
            d = n[("abst1", "lula2")] * qL + n[("abst1", "flavio2")] * qF + n[("abst1", "bn2")] * P[3]
            d += p["lam_S"] * (n[("flavio1", "lula2")] * (P[0] - P[1]) + n[("lula1", "flavio2")] * (P[1] - P[0]))
            d += p["lam_O"] * (n[("outros1", "lula2")] * (P[0] - avg) + n[("outros1", "flavio2")] * (P[1] - avg))
            d += p["lam_BN"] * (n[("bn1", "lula2")] * (P[0] - pbn) + n[("bn1", "flavio2")] * (P[1] - pbn))
            if p["tau_L"] or p["tau_F"]:
                if cargo == "dep":
                    for tau, row, alvo in ((p["tau_L"], 0, ICL), (p["tau_F"], 1, IPL)):
                        mv = np.zeros(len(BL))
                        cen = P[row][[2, 3]] * tau
                        mv[[2, 3]] -= cen
                        mv[alvo] += cen.sum()
                        d += n[(("lula1", "lula2") if row == 0 else ("flavio1", "flavio2"))] * mv
                else:
                    for tau, row, campo in ((p["tau_L"], 0, "L"), (p["tau_F"], 1, "F")):
                        neut = (m["scampo"] == "N") & (np.arange(len(m["scols"])) != m["ibn_s"])
                        alvo = np.where(m["scampo"] == campo)[0]
                        if len(alvo) == 0:
                            continue
                        mv = np.zeros(P.shape[1])
                        tira = P[row] * neut * tau
                        mv -= tira
                        w = m["sv_col"][alvo] / m["sv_col"][alvo].sum()
                        mv[alvo] += tira.sum() * w
                        q = cap_senado(P[row] + mv, m["ibn_s"])
                        d += n[(("lula1", "lula2") if row == 0 else ("flavio1", "flavio2"))] * (q - P[row])
            if p["demob"]:
                d -= (n[("lula1", "abst2")] * P[0] + n[("flavio1", "abst2")] * P[1]
                      + n[("outros1", "abst2")] * avg + n[("bn1", "abst2")] * pbn)
            if cargo == "dep":
                dv = np.zeros(len(s["agr"]))
                for b in range(4):
                    mask = s["agr_b"] == b
                    tot = s["agr_v"][mask].sum()
                    if tot <= 0:
                        continue
                    share = s["agr_v"][mask] / tot
                    if b == ICL and d[b] > 0 and p["kappa"] > 0 and "PCDOB / PT / PV" in s["agr"]:
                        pt = np.array([a == "PCDOB / PT / PV" for a in np.array(s["agr"])[mask]], float)
                        share = (1 - p["kappa"]) * share + p["kappa"] * pt
                    dv[mask] = d[b] * share
                novo = np.maximum(s["agr_v"] + dv, 0)
                agrs = {a: {"votos": int(round(novo[i])),
                            "cands": (s["cands"][i] * (novo[i] / s["agr_v"][i] if s["agr_v"][i] else 1)).tolist()}
                        for i, a in enumerate(s["agr"])}
                res, _ = distribuir(agrs, s["vagas_uf"], sum(a["votos"] for a in agrs.values()))
                for i, a in enumerate(s["agr"]):
                    for part in s["parts"][i][:res[a]]:
                        if part == "PL":
                            out["PL"] += 1
                        elif part in L_PART:
                            out["colig"] += 1
                            out["PT"] += part == "PT"
                        else:
                            out["outros"] += 1
            else:
                dvs = d @ m["E"]
                novo = s["sen_v"] + dvs
                order = np.argsort(-novo)
                win = np.zeros(len(novo), bool)
                win[order[:2]] = True
                for c in ("L", "F", "N"):
                    out[f"sen_{c}"] += int(((s["sen_campo"] == c) & win).sum())
                sai = [s["sen_nome"][i] for i in np.where(s["sen_eleito"] & ~win)[0]]
                ent = [s["sen_nome"][i] for i in np.where(~s["sen_eleito"] & win)[0]]
                for a, b in zip(sai, ent):
                    flips.append(f"{uf}: {a} -> {b}")
                margens[uf] = novo[order[1]] - novo[order[2]]
                if uf == "RJ":
                    iB = s["sen_num"].index("131")
                    iJ = s["sen_num"].index("221")
                    out["RJ_jordy_menos_benedita"] = novo[iJ] - novo[iB]
    out["sen_flips"] = "; ".join(flips) if flips else "nenhuma"
    return out


if __name__ == "__main__":
    M = load_model(20)
    r = run({}, M)
    print("caso-base:", r)
