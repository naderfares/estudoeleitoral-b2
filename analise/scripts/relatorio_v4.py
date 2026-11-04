"""Gera as tabelas do relatório a partir de results4/ (só leitura; não roda o motor).

Uso: python3 -I scripts/relatorio_v4.py > results4/tabelas.md
"""
import json
from pathlib import Path

import pandas as pd

R = Path(__file__).resolve().parents[1] / "results4"
p = pd.read_csv(R / "principal.csv")
b = pd.read_csv(R / "bootstrap.csv")
s = pd.read_csv(R / "sensibilidade.csv")
c = pd.read_csv(R / "clima.csv")
h = json.load(open(R / "hipoteses.json"))
m = json.load(open(R / "manifesto.json"))
NOME = {"L": "Campanha de Lula", "F": "Campanha de Flávio", "comum": "Comum", "total": "Total"}


def ic(x):
    return f"{x.quantile(0.025):+.0f} a {x.quantile(0.975):+.0f}"


def sinal(v):
    return f"{v:+.0f}" if v else "0"


print("## Canal C (comparecimento), efeito partidário em cadeiras\n")
print("| Braço | PL | IC 95% | Coligação de Lula | IC 95% | Centro-direita | Centro e demais |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for br in ("L", "F", "comum", "total"):
    r = p[(p.braco == br) & (p.config == "C+P") & (p.lam == 0)].iloc[0]
    bb = b[(b.braco == br) & (b.lam == 0)]
    print(f"| {NOME[br]} | {sinal(r.ef_PL)} | {ic(bb.ef_PL)} | {sinal(r.ef_colig)} | {ic(bb.ef_colig)} | {sinal(r.ef_cdir)} | {sinal(r.ef_cdem)} |")

print("\n## Curva de arrasto (canal C + persuasão), efeito partidário em cadeiras\n")
print("| Braço | λ | PL | IC 95% | Coligação de Lula | IC 95% | Reamostragens com mudança relevante |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for br in ("L", "F", "total"):
    for lam in (0.0, 0.5, 1.0):
        r = p[(p.braco == br) & (p.config == "C+P") & (p.lam == lam)].iloc[0]
        bb = b[(b.braco == br) & (b.lam == lam)]
        rel = ((bb.ef_PL.abs() >= 10) | (bb.ef_colig.abs() >= 10)).mean()
        lt, rt = f"{lam:.1f}".replace(".", ","), f"{rel:.1%}".replace(".", ",")
        print(f"| {NOME[br]} | {lt} | {sinal(r.ef_PL)} | {ic(bb.ef_PL)} | {sinal(r.ef_colig)} | {ic(bb.ef_colig)} | {rt} |")

print("\n## Senado, braço total\n")
print("| λ | Trocas de eleito |")
print("| --- | --- |")
for lam in (0.0, 0.5, 1.0):
    r = p[(p.braco == "total") & (p.config == "C+P") & (p.lam == lam)].iloc[0]
    print(f"| {lam:.1f} | {r.sen_flips} |".replace(".", ",", 1))

print("\n## Sensibilidade, braço total, efeito partidário (PL / coligação)\n")
print("| Variante | λ = 0 | λ = 0,5 | λ = 1 |")
print("| --- | --- | --- | --- |")
for v in s.variante.unique():
    g = s[(s.variante == v) & (s.braco == "total")].set_index("lam")
    print(f"| {v} | " + " | ".join(f"{sinal(g.loc[l, 'ef_PL'])} / {sinal(g.loc[l, 'ef_colig'])}" for l in (0.0, 0.5, 1.0)) + " |")

print("\n## Canal clima (só limite), variação em cadeiras contra o real\n")
print("| Lado | τ | PL | Coligação de Lula | Centro-direita | Centro e demais |")
print("| --- | --- | --- | --- | --- | --- |")
for r in c.itertuples():
    print(f"| {NOME[r.braco]} | {r.tau:.2f}".replace(".", ",") + f" | {sinal(r.d_PL)} | {sinal(r.d_colig)} | {sinal(r.d_cdir)} | {sinal(r.d_cdem)} |")

print("\n## Decisões pré-registradas (como gravadas em hipoteses.json)\n")
for d in h:
    extra = {k: v for k, v in d.items() if v is not None and k not in ("hipotese", "braco", "resultado")}
    print(f"- {d['hipotese']}, {d['braco']}: **{d['resultado']}** ({extra})")
print(f"\nPiso de ruído (P95, 1%): {m['p95_ruido']}. Real: {m['real']}. B = {m['B']}. Início da corrida: {m['inicio']}.")
