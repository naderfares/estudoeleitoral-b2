"""Teste do modelo bayesiano R×C (ei_bayes.py) com dados sintéticos de valor verdadeiro conhecido.

Não usa nenhum dado eleitoral. Gera unidades com taxas heterogêneas a partir de uma tabela verdadeira, ajusta o
modelo e confere: (1) convergência; (2) cobertura dos intervalos de 95% sobre as taxas agregadas verdadeiras;
(3) erro médio comparado ao da regressão de Goodman com restrições, nas mesmas unidades.

Uso: python3 -I scripts/teste_ei_bayes.py [--unidades 120] [--sorteios 400] [--aquecimento 500] [--cadeias 2]
"""
import argparse
import sys
from pathlib import Path

import cvxpy as cp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ei_bayes import ajusta, limites  # noqa: E402


def goodman(Xc, Tc):
    N = Xc.sum(1)
    X = Xc / N[:, None]
    Y = Tc / Tc.sum(1)[:, None]
    w = N / N.sum()
    P = cp.Variable((X.shape[1], Y.shape[1]))
    obj = cp.sum_squares(cp.multiply(np.sqrt(w)[:, None], Y - X @ P))
    cp.Problem(cp.Minimize(obj), [P >= 0, cp.sum(P, axis=1) == 1]).solve(solver=cp.CLARABEL)
    return np.clip(P.value, 0, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unidades", type=int, default=120)
    ap.add_argument("--sorteios", type=int, default=400)
    ap.add_argument("--aquecimento", type=int, default=500)
    ap.add_argument("--cadeias", type=int, default=2)
    ap.add_argument("--centrada", action="store_true")
    ap.add_argument("--alvo", type=float, default=0.99)
    a = ap.parse_args()
    rng = np.random.default_rng(11)
    R, C, n = 4, 5, a.unidades
    mu = rng.dirichlet(np.ones(C) * 0.8, size=R)
    d = 30.0
    N = rng.integers(2000, 20000, n)
    comp = rng.dirichlet(np.array([3.0, 3.0, 1.0, 0.6]), size=n)
    Xc = np.vstack([rng.multinomial(N[i], comp[i]) for i in range(n)])
    cel = np.zeros((n, R, C))
    for i in range(n):
        for r in range(R):
            b = rng.dirichlet(d * mu[r])
            cel[i, r] = rng.multinomial(Xc[i, r], b)
    Tc = cel.sum(1)
    verdade = cel.sum(0) / Xc.sum(0)[:, None]

    S, dg = ajusta(Xc, Tc, a.sorteios // a.cadeias, a.aquecimento, a.cadeias, 7, centrada=a.centrada, alvo=a.alvo)
    lo, hi = np.quantile(S, [0.025, 0.975], axis=0)
    cob = float(((verdade >= lo) & (verdade <= hi)).mean())
    err_b = float(np.abs(S.mean(0) - verdade).mean())
    err_g = float(np.abs(goodman(Xc, Tc) - verdade).mean())
    dmin, dmax = limites(Xc, Tc)
    dentro = bool(((verdade >= dmin - 1e-9) & (verdade <= dmax + 1e-9)).all())

    print(f"unidades {n}, tabela {R}x{C}, parametrização {'centrada' if a.centrada else 'não centrada'}, alvo {a.alvo}")
    print(f"R-hat máximo {dg['rhat_max']:.3f}; ESS mínimo {dg['ess_min']:.0f}; divergências {dg['divergencias']}")
    print(f"cobertura dos intervalos de 95%: {cob:.2f}")
    print(f"erro absoluto médio: bayesiano {err_b:.4f}; Goodman {err_g:.4f}")
    print(f"verdade dentro dos limites de Duncan e Davis: {dentro}")
    print("R-hat por célula:", dg["rhat_celulas"])
    falhas = []
    if not (dg["rhat_max"] < 1.01 and dg["ess_min"] >= 400):
        falhas.append("convergência (R-hat < 1,01 e ESS >= 400, o critério do adendo)")
    if cob < 0.85:
        falhas.append("cobertura")
    if err_b > 1.5 * err_g:
        falhas.append("erro maior que 1,5 vez o de Goodman")
    if not dentro:
        falhas.append("limites")
    print("todos os critérios atendidos" if not falhas else "FALHA: " + ", ".join(falhas))
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
