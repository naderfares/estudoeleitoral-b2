"""Figuras do artigo a partir dos resultados pré-registrados (results4) e dos fluxos (results2_n0_20).

Saída: documentos/figuras/fig*.jpg em 300 dpi, mais uma versão em tons de cinza de cada uma (_cinza.jpg).
Vermelho identifica a coligação de Lula e azul o PL, com a mesma intensidade. Nas barras, os dois lados têm
hachuras espelhadas; nas linhas e pontos, marcadores diferentes (círculo e quadrado), para continuar legíveis
em preto e branco sem destacar um lado. A ordem das séries segue a ordem da Tabela 1 (Lula, depois Flávio).

Uso: python3 -I scripts/figuras_v4.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

A = Path(__file__).resolve().parents[1]
R4 = A / "results4"
OUT = A.parent / "documentos" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)
VERM, AZUL, CINZA = "#c0392b", "#2c5fa8", "#7f7f7f"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})


def salvar(fig, nome):
    p = OUT / f"{nome}.jpg"
    fig.savefig(p, dpi=300, bbox_inches="tight", pil_kwargs={"quality": 95})
    Image.open(p).convert("L").save(OUT / f"{nome}_cinza.jpg", quality=95, dpi=(300, 300))
    plt.close(fig)


# Figura 1: origem dos votos ganhos por cada finalista entre os turnos
f = pd.read_csv(A / "results2_n0_20" / "fluxos_por_uf.csv")
t = f.groupby(["origem", "destino"]).votos.sum().unstack() / 1e6
orig = [("abst1", "Abstenção no 1º turno"), ("outros1", "Outros presidenciáveis"), ("bn1", "Branco ou nulo"), ("troca", "Outro finalista")]
lula = [t.loc["abst1", "lula2"], t.loc["outros1", "lula2"], t.loc["bn1", "lula2"], t.loc["flavio1", "lula2"]]
flav = [t.loc["abst1", "flavio2"], t.loc["outros1", "flavio2"], t.loc["bn1", "flavio2"], t.loc["lula1", "flavio2"]]
fig, ax = plt.subplots(figsize=(7, 3.6))
y = np.arange(len(orig))
ax.barh(y + 0.2, lula, 0.38, color=VERM, label="Para Lula", edgecolor="black", linewidth=0.4, hatch="\\\\\\")
ax.barh(y - 0.2, flav, 0.38, color=AZUL, label="Para Flávio", edgecolor="black", linewidth=0.4, hatch="///")
for yi, (a, b) in enumerate(zip(lula, flav)):
    ax.text(a + 0.05, yi + 0.2, f"{a:.1f}".replace(".", ","), va="center", fontsize=8)
    ax.text(b + 0.05, yi - 0.2, f"{b:.1f}".replace(".", ","), va="center", fontsize=8)
ax.set_yticks(y, [o[1] for o in orig])
ax.invert_yaxis()
ax.set_xlabel("Milhões de eleitores (estimativa de inferência ecológica)")
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
ax.legend(frameon=False, loc="lower right")
salvar(fig, "fig1_origem_dos_votos")

# Figura 2: canal de comparecimento por braço, efeito partidário com IC 95% e piso de ruído
p = pd.read_csv(R4 / "principal.csv")
b = pd.read_csv(R4 / "bootstrap.csv")
bracos = [("L", "Campanha\nde Lula"), ("F", "Campanha\nde Flávio"), ("comum", "Comum"), ("total", "Total")]
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.axhspan(-2, 2, color="#dddddd", zorder=0, label="Piso de ruído (± 2)")
ax.axhline(0, color="black", linewidth=0.6)
for k, (br, _) in enumerate(bracos):
    pt = p[(p.braco == br) & (p.config == "C+P") & (p.lam == 0)].iloc[0]
    bb = b[(b.braco == br) & (b.lam == 0)]
    for dx, col, cor, mk, lab in ((-0.12, "ef_colig", VERM, "o", "Coligação de Lula"), (0.12, "ef_PL", AZUL, "s", "PL")):
        lo, hi = bb[col].quantile(0.025), bb[col].quantile(0.975)
        ax.errorbar(k + dx, pt[col], yerr=[[pt[col] - lo], [hi - pt[col]]], fmt=mk, color=cor, capsize=3,
                    markeredgecolor="black", label=lab if k == 0 else None)
ax.set_xticks(range(len(bracos)), [x[1] for x in bracos])
ax.set_ylabel("Cadeiras contra o placebo")
ax.set_ylim(-6, 6)
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.15))
salvar(fig, "fig2_comparecimento_por_braco")

# Figura 3: curva de arrasto
fig, axs = plt.subplots(1, 3, figsize=(8.5, 3.2), sharey=True)
for ax, (br, nome) in zip(axs, [("L", "Campanha de Lula"), ("F", "Campanha de Flávio"), ("total", "Total")]):
    cur = p[(p.braco == br) & (p.config == "C+P")].sort_values("lam")
    bb = b[b.braco == br].groupby("lam")
    for col, cor, mk, ls, lab in (("ef_colig", VERM, "o", "-", "Coligação de Lula"), ("ef_PL", AZUL, "s", "-", "PL")):
        ax.plot(cur.lam, cur[col], color=cor, marker=mk, markersize=3.5, linestyle=ls, label=lab)
        q = bb[col].quantile([0.025, 0.975]).unstack()
        ax.fill_between(q.index, q[0.025], q[0.975], color=cor, alpha=0.15, linewidth=0)
    for s in (10, -10):
        ax.axhline(s, color="black", linewidth=0.6, linestyle=":")
    ax.axhspan(-2, 2, color="#dddddd", zorder=0)
    ax.set_title(nome, fontsize=10)
    ax.set_xlabel("Arrasto λ")
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "0,25", "0,5", "0,75", "1"])
axs[0].set_ylabel("Cadeiras contra o placebo")
axs[0].legend(frameon=False, fontsize=8, loc="upper left")
salvar(fig, "fig3_curva_de_arrasto")

# Figura 4: canal clima (limite)
c = pd.read_csv(R4 / "clima.csv")
fig, ax = plt.subplots(figsize=(7, 3.4))
lados = [("L", "Eleitores fiéis\nde Lula"), ("F", "Eleitores fiéis\nde Flávio"), ("total", "Os dois")]
taus = [0.05, 0.10, 0.20]
w = 0.12
for i, (br, _) in enumerate(lados):
    for j, tau in enumerate(taus):
        r = c[(c.braco == br) & (c.tau == tau)].iloc[0]
        x = i + (j - 1) * 2.2 * w
        ax.bar(x - w / 2, r.d_colig, w, color=VERM, edgecolor="black", linewidth=0.4, hatch="\\\\\\", label="Coligação de Lula" if i == j == 0 else None)
        ax.bar(x + w / 2, r.d_PL, w, color=AZUL, edgecolor="black", linewidth=0.4, hatch="///", label="PL" if i == j == 0 else None)
        ax.text(x, max(r.d_colig, r.d_PL) + 1, f"τ={tau:.2f}".replace(".", ","), ha="center", fontsize=7)
ax.axhline(0, color="black", linewidth=0.6)
ax.set_xticks(range(len(lados)), [x[1] for x in lados])
ax.set_ylabel("Cadeiras contra o resultado real")
ax.legend(frameon=False)
salvar(fig, "fig4_canal_clima")
print("figuras em", OUT)
