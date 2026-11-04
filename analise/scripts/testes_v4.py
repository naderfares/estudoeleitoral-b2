"""Testes contábeis do motor v4. Não imprimem resultados de cenários: só passa ou falha.

Uso: python3 -I scripts/testes_v4.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor_v4 as mv  # noqa: E402

bh = mv.bh
M = mv.carregar(20)
falhas = []


def checa(nome, ok):
    print(("ok    " if ok else "FALHA ") + nome)
    if not ok:
        falhas.append(nome)


# 1. Sem nenhum canal, o motor devolve a Câmara e o Senado reais
real = {"PL": 0, "colig": 0, "cdir": 0, "cdem": 0}
for uf in mv.UFS:
    s = mv.ST[uf]
    g = bh.cp_api[bh.cp_api.uf == uf].groupby("agremiacao").vagas_agr_oficial.first()
    for i, a in enumerate(s["agr"]):
        real[mv.NOMES[int(s["agr_b"][i])]] += int(g[a])
r0 = mv.run_v4({}, M)
checa("contrafactual zerado reproduz as 513 vagas por bloco", all(r0[k] == real[k] for k in real) and sum(real.values()) == 513)
sen_real = sum(int(mv.ST[uf]["sen_eleito"].sum()) for uf in mv.UFS)
checa("contrafactual zerado reproduz os eleitos do Senado", r0["sen_flips"] == "nenhuma" and r0["sen_L"] + r0["sen_F"] + r0["sen_N"] == sen_real)
checa("contrafactual zerado não move votos", np.allclose(r0["dv_nac"], 0))

# 2. A permuta mu/nu preserva as margens dos dois turnos em todas as UFs
ok = True
for uf in mv.UFS:
    m = M[uf]
    p = {**mv.BASE, "mu": 1.0, "nu": 1.0}
    a, b = m["n"], mv.fluxos(m, p)
    for o in ("lula1", "flavio1", "outros1", "bn1", "abst1"):
        ok &= abs(sum(v for (x, _), v in a.items() if x == o) - sum(v for (x, _), v in b.items() if x == o)) < 1e-6
    for d in ("lula2", "flavio2", "bn2", "abst2"):
        ok &= abs(sum(v for (_, y), v in a.items() if y == d) - sum(v for (_, y), v in b.items() if y == d)) < 1e-6
    ok &= min(b.values()) >= -1e-9
checa("permuta mu/nu preserva linhas e colunas e não gera fluxo negativo", ok)

# 3. Perfis: deputado soma 1, Senado soma 2 (dois votos)
ok = True
for uf in mv.UFS:
    ok &= np.allclose(M[uf]["P"].sum(1), 1, atol=1e-6)
    ok &= np.allclose(M[uf]["Ps"].sum(1), 2, atol=1e-3)
checa("perfis de deputado somam 1 e de Senado somam 2", ok)

# 4. Os braços somam o total (linearidade nos votos)
cfg = {"C": True, "lam_P": 1.0, "clima": True, "tau_L": 0.1, "tau_F": 0.1, "mu": 0.3, "nu": 0.3}
tot = mv.run_v4(cfg, M)["dv_nac"]
soma = sum(mv.run_v4({**cfg, "arms": (a,)}, M)["dv_nac"] for a in mv.ARMS)
checa("braços L + F + comum somam o total", np.allclose(tot, soma, rtol=1e-9, atol=1e-3))

# 5. Canal C: votos legislativos novos = entradas menos saídas (rho = 0), com e sem placebo
ent = sai = 0.0
for uf in mv.UFS:
    n = M[uf]["n"]
    ent += sum(n[("abst1", d)] for d in ("lula2", "flavio2", "bn2"))
    sai += sum(n[(o, "abst2")] for o in ("lula1", "flavio1", "outros1", "bn1"))
for plac in (False, True):
    dv = mv.run_v4({"C": True, "placebo": plac}, M)["dv_nac"]
    checa(f"canal C soma entradas menos saídas (placebo={plac})", abs(dv.sum() - (ent - sai)) < 1.0)

# 6. Canal P não cria nem destrói votos (só troca de bloco)
dv = mv.run_v4({"lam_P": 1.0}, M)["dv_nac"]
checa("canal P preserva o total de votos", abs(dv.sum()) < 1.0)

# 7. Efeito mecânico: o excesso vai para no máximo um lado e não passa do fluxo total
ok = True
for uf in mv.UFS:
    n, rows = M[uf]["n"], mv.ST[uf]["rows"]
    for mec in ("proporcional", "datafolha"):
        eL, eF = mv.excesso_outros(n, rows, mec)
        ok &= eL >= 0 and eF >= 0 and min(eL, eF) == 0
        ok &= eL <= n[("outros1", "lula2")] + 1e-6 and eF <= n[("outros1", "flavio2")] + 1e-6
checa("excesso sobre a divisão mecânica é unilateral e limitado", ok)

# 8. Sem parâmetro assimétrico no caso-base
b = mv.BASE
checa("caso-base simétrico (alpha e tau iguais para os dois lados)", b["alpha_L"] == b["alpha_F"] and b["tau_L"] == b["tau_F"])

print()
print("todos os testes passaram" if not falhas else f"{len(falhas)} teste(s) falharam")
raise SystemExit(1 if falhas else 0)
