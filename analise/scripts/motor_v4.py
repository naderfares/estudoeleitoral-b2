"""Motor v4 do contrafactual (03/11/2026).

Corrige os problemas apontados na revisão crítica e trata as duas campanhas finalistas com a mesma régua.

O que mudou em relação a behaviors.py (v3):
  1. mu e nu viraram uma permuta 2x2 que preserva as margens dos dois turnos (antes criavam eleitores)
     e valem igualmente para os fluxos que vão a Lula e a Flávio.
  2. Branco/nulo e outros candidatos usam os perfis estimados (P[3] e P[2]) em todo o motor
     (antes: "60% branco + 40% média" e média da UF).
  3. Saídas ligadas por padrão: quem votou no 1º turno e faltou no 2º perde o voto legislativo.
  4. Efeito mecânico descontado: os eleitores dos outros presidenciáveis precisam escolher um lado no 2º turno;
     só o excesso sobre uma divisão neutra (proporcional aos votos válidos dos finalistas no 1º turno da UF)
     conta como efeito de campanha.
  5. Canais separados: C (comparecimento: entradas e saídas), P (persuasão de quem já votava, com arrasto lam_P
     de 0 a 1) e clima (tau_L, tau_F, só como limite).
  6. Braços por campanha: L (fluxos que terminam em Lula), F (fluxos que terminam em Flávio) e comum
     (entradas em branco/nulo, saídas e passagens de um finalista para branco/nulo). Os votos somam por
     linearidade; as cadeiras são calculadas para cada braço e para o total.
  7. Cadeiras contadas por bloco da agremiação (PL, coligação de Lula, centro-direita, centro e demais).
  8. Placebo neutro do canal C: entradas e saídas votam como o eleitor médio da UF.
  9. Sem kappa (só existia para um dos lados).

Este arquivo não roda cenários sozinho. A análise pré-registrada está em rodar_preregistro.py.
"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("ESTUDO_ROOT", Path(__file__).resolve().parents[1]))
_argv = sys.argv
sys.argv = [_argv[0], str(ROOT)]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import behaviors as bh  # noqa: E402  (carrega os dados estáticos do TSE)
sys.argv = _argv

ST, UFS, BL = bh.ST, bh.UFS, bh.BL
IPL, ICL, IBN = bh.IPL, bh.ICL, bh.IBN
ICD, ICM = 2, 3  # centro_direita, centro_demais
NOMES = {IPL: "PL", ICL: "colig", ICD: "cdir", ICM: "cdem"}
ARMS = ("L", "F", "comum")

BASE = dict(
    C=False,          # canal de comparecimento
    lam_P=0.0,        # arrasto do canal de persuasão (0 = desligado, 1 = arrasto total)
    clima=False,      # canal clima (tau_L, tau_F)
    arms=ARMS,        # braços incluídos
    alpha_L=0.0, alpha_F=0.0, rho=0.0, geo=0,
    saidas=True,
    placebo=False,    # canal C com perfil neutro (média da UF)
    mec="proporcional",  # "proporcional", "nenhum" ou "datafolha"
    mu=0.0, nu=0.0,
    tau_L=0.0, tau_F=0.0,
)
DATAFOLHA_S_L = 32 / (32 + 46)  # Datafolha 8/10: eleitores de Cury, Renan, Caiado e Zema (32% Lula, 46% Flávio)


def carregar(n0=20, pasta=None):
    """Modelo estimado (fluxos e perfis). pasta = subpasta de results2_n0_* (ex.: 'boot/b7')."""
    return bh.load_model(pasta if pasta is not None else n0)


def fluxos(m, p):
    """Fluxos da UF com a permuta mu/nu, que preserva todas as margens dos dois turnos."""
    n = dict(m["n"])
    for par, orig in (("mu", "bn1"), ("nu", "outros1")):
        if not p[par]:
            continue
        xs = {d: p[par] * n[(orig, d)] for d in ("lula2", "flavio2")}
        cap = n[("abst1", "abst2")]
        tot = sum(xs.values())
        if tot > cap > 0:
            xs = {d: x * cap / tot for d, x in xs.items()}
        for d, x in xs.items():
            n[(orig, d)] -= x
            n[("abst1", d)] += x
            n[("abst1", "abst2")] -= x
            n[(orig, "abst2")] += x
    return n


def excesso_outros(n, rows, mec):
    """Eleitores de outros presidenciáveis atribuídos a cada campanha, descontado o efeito mecânico."""
    oL, oF = n[("outros1", "lula2")], n[("outros1", "flavio2")]
    if mec == "nenhum":
        return oL, oF
    s = DATAFOLHA_S_L if mec == "datafolha" else rows[0] / (rows[0] + rows[1])
    e = oL - (oL + oF) * s
    return max(e, 0.0), max(-e, 0.0)


def _perfis(cargo, s, m, p):
    if cargo == "dep":
        P, avg = m["P"], s["avg_dep"]
        eBN = np.eye(len(BL))[IBN]
        bL = m["geo_L"] if p["geo"] else P[0]
        bF = m["geo_F"] if p["geo"] else P[1]
        milL, milF = bh.militante_dep(bL, ICL), bh.militante_dep(bF, IPL)
    else:
        P, avg = m["Ps"], m["avg_s"]
        eBN = np.zeros(P.shape[1])
        eBN[m["ibn_s"]] = 2.0
        bL = m["geo_Ls"] if p["geo"] else P[0]
        bF = m["geo_Fs"] if p["geo"] else P[1]
        milL, milF = bh.militante_sen(bL, m, "L"), bh.militante_sen(bF, m, "F")
    qL = (1 - p["rho"]) * bh.tilt(bL, p["alpha_L"], avg, milL) + p["rho"] * eBN
    qF = (1 - p["rho"]) * bh.tilt(bF, p["alpha_F"], avg, milF) + p["rho"] * eBN
    return P, avg, qL, qF


def _clima(cargo, s, m, P, n, tau, row):
    if not tau:
        return 0.0
    leal = n[("lula1", "lula2")] if row == 0 else n[("flavio1", "flavio2")]
    if cargo == "dep":
        alvo = ICL if row == 0 else IPL
        mv = np.zeros(len(BL))
        cen = P[row][[ICD, ICM]] * tau
        mv[[ICD, ICM]] -= cen
        mv[alvo] += cen.sum()
        return leal * mv
    campo = "L" if row == 0 else "F"
    neut = (m["scampo"] == "N") & (np.arange(len(m["scols"])) != m["ibn_s"])
    alvo = np.where(m["scampo"] == campo)[0]
    if len(alvo) == 0:
        return 0.0
    mv = np.zeros(P.shape[1])
    tira = P[row] * neut * tau
    mv -= tira
    w = m["sv_col"][alvo] / m["sv_col"][alvo].sum()
    mv[alvo] += tira.sum() * w
    q = bh.cap_senado(P[row] + mv, m["ibn_s"])
    return leal * (q - P[row])


def deltas(uf, m, p, cargo):
    """Variação de votos por coluna do perfil (blocos no caso de deputado), separada por braço."""
    s = ST[uf]
    n = fluxos(m, p)
    P, avg, qL, qF = _perfis(cargo, s, m, p)
    z = np.zeros(P.shape[1])
    d = {a: z.copy() for a in ARMS}
    if p["C"]:
        pL, pF, pB = (avg, avg, avg) if p["placebo"] else (qL, qF, P[3])
        d["L"] += n[("abst1", "lula2")] * pL
        d["F"] += n[("abst1", "flavio2")] * pF
        d["comum"] += n[("abst1", "bn2")] * pB
        if p["saidas"]:
            for i, o in enumerate(("lula1", "flavio1", "outros1", "bn1")):
                d["comum"] -= n[(o, "abst2")] * (avg if p["placebo"] else P[i])
    lam = p["lam_P"]
    if lam:
        eL, eF = excesso_outros(n, s["rows"], p["mec"])
        d["L"] += lam * (n[("flavio1", "lula2")] * (P[0] - P[1]) + n[("bn1", "lula2")] * (P[0] - P[3]) + eL * (P[0] - P[2]))
        d["F"] += lam * (n[("lula1", "flavio2")] * (P[1] - P[0]) + n[("bn1", "flavio2")] * (P[1] - P[3]) + eF * (P[1] - P[2]))
        d["comum"] += lam * (n[("lula1", "bn2")] * (P[3] - P[0]) + n[("flavio1", "bn2")] * (P[3] - P[1]))
    if p["clima"]:
        d["L"] += _clima(cargo, s, m, P, n, p["tau_L"], 0)
        d["F"] += _clima(cargo, s, m, P, n, p["tau_F"], 1)
    return d


def run_v4(par, M, perturba=None):
    """Roda o contrafactual. perturba: dict uf -> fatores multiplicativos dos votos das listas (piso de ruído)."""
    p = {**BASE, **par}
    out = {"PL": 0, "colig": 0, "cdir": 0, "cdem": 0, "sen_L": 0, "sen_F": 0, "sen_N": 0}
    dv_nac = np.zeros(len(BL))
    flips, margem_sen = [], {}
    for uf in UFS:
        s, m = ST[uf], M[uf]
        # Câmara
        dd = deltas(uf, m, p, "dep")
        d = sum(dd[a] for a in p["arms"])
        dv_nac += d
        dv = np.zeros(len(s["agr"]))
        for b in range(4):
            mask = s["agr_b"] == b
            tot = s["agr_v"][mask].sum()
            if tot > 0:
                dv[mask] = d[b] * s["agr_v"][mask] / tot
        base = s["agr_v"] * (perturba[uf] if perturba is not None else 1.0)
        novo = np.maximum(base + dv, 0)
        agrs = {a: {"votos": int(round(novo[i])),
                    "cands": (s["cands"][i] * (novo[i] / s["agr_v"][i] if s["agr_v"][i] else 1)).tolist()}
                for i, a in enumerate(s["agr"])}
        res, _ = bh.distribuir(agrs, s["vagas_uf"], sum(a["votos"] for a in agrs.values()))
        for i, a in enumerate(s["agr"]):
            out[NOMES[int(s["agr_b"][i])]] += res[a]
        # Senado
        ds = deltas(uf, m, p, "sen")
        dsum = sum(ds[a] for a in p["arms"])
        nv = s["sen_v"] + dsum @ m["E"]
        order = np.argsort(-nv)
        win = np.zeros(len(nv), bool)
        win[order[:2]] = True
        for c in ("L", "F", "N"):
            out[f"sen_{c}"] += int(((s["sen_campo"] == c) & win).sum())
        sai = [s["sen_nome"][i] for i in np.where(s["sen_eleito"] & ~win)[0]]
        ent = [s["sen_nome"][i] for i in np.where(~s["sen_eleito"] & win)[0]]
        flips += [f"{uf}: {a} -> {b}" for a, b in zip(sai, ent)]
        margem_sen[uf] = float(nv[order[1]] - nv[order[2]])
    out["sen_flips"] = "; ".join(flips) if flips else "nenhuma"
    out["dv_nac"] = dv_nac
    out["margem_sen"] = margem_sen
    return out


def ruido(M, sd, draws, seed=2026):
    """Piso de ruído: perturba os votos de cada lista por um fator lognormal (desvio sd) e mede a troca de cadeiras."""
    rng = np.random.default_rng(seed)
    real = run_v4({}, M)
    rows = []
    for _ in range(draws):
        pert = {uf: np.exp(rng.normal(0, sd, len(ST[uf]["agr"]))) for uf in UFS}
        r = run_v4({}, M, perturba=pert)
        rows.append({k: r[k] - real[k] for k in ("PL", "colig", "cdir", "cdem")})
    return rows
