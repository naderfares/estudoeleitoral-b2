"""Distribuição de cadeiras da Câmara (Código Eleitoral arts. 106-109,
Lei 14.211/2021, e decisão do STF nas ADIs 7228/7263/7325 sobre a 3ª fase das sobras).

Entrada por UF: dict agremiacao -> {"votos": int, "cands": [votos dos candidatos]}.
"""
from decimal import Decimal, ROUND_HALF_DOWN


def quociente_eleitoral(votos_validos, vagas):
    # fração igual ou inferior a meio é desprezada; superior a meio, arredonda para 1
    return int((Decimal(votos_validos) / Decimal(vagas)).quantize(Decimal(1), rounding=ROUND_HALF_DOWN))


def distribuir(agrs, vagas, votos_validos=None):
    if votos_validos is None:
        votos_validos = sum(a["votos"] for a in agrs.values())
    qe = quociente_eleitoral(votos_validos, vagas)
    cand = {k: sorted(a["cands"], reverse=True) for k, a in agrs.items()}
    eleitos = {k: 0 for k in agrs}

    # 1ª fase: quociente partidário, só com candidatos com >= 10% do QE
    for k, a in agrs.items():
        qp = a["votos"] // qe
        aptos = sum(1 for v in cand[k] if v >= 0.10 * qe)
        eleitos[k] = min(qp, aptos)
    restantes = vagas - sum(eleitos.values())

    def proximo_cand(k):
        i = eleitos[k]
        return cand[k][i] if i < len(cand[k]) else None

    # 2ª fase: médias, partidos com >= 80% do QE e candidato com >= 20% do QE
    while restantes > 0:
        elig = [k for k, a in agrs.items()
                if a["votos"] >= 0.80 * qe and (proximo_cand(k) or 0) >= 0.20 * qe]
        if not elig:
            break
        k = max(elig, key=lambda k: (agrs[k]["votos"] / (eleitos[k] + 1), agrs[k]["votos"]))
        eleitos[k] += 1
        restantes -= 1

    # 3ª fase (STF): todas as agremiações, sem cláusulas de desempenho
    while restantes > 0:
        elig = [k for k in agrs if proximo_cand(k) is not None]
        k = max(elig, key=lambda k: (agrs[k]["votos"] / (eleitos[k] + 1), agrs[k]["votos"]))
        eleitos[k] += 1
        restantes -= 1

    return eleitos, qe
