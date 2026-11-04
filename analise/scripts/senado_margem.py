"""Para cada UF: swing (p.p. bipartidário) necessário para o melhor candidato do campo de Lula
não eleito ultrapassar o último eleito que não é do campo de Lula. Compara com o swing real."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RES = Path(sys.argv[1])
sen = pd.read_csv(RES / "senado_simulacao.csv", keep_default_na=False)
sw = pd.read_csv(RES / "swing_por_uf.csv", index_col=0)

rows = []
for nome in ["restrito_uf", "amplo_uf"]:
    campo = f"campo_{nome}"
    for uf, g in sen.groupby("uf"):
        g = g.copy()
        vagas = int(g.vagas.iloc[0])
        L = g.loc[g[campo] == "L", "votos"].sum()
        F = g.loc[g[campo] == "F", "votos"].sum()

        def eleitos(delta):
            v = g.votos.astype(float).copy()
            if L and F:
                T = min(delta * (L + F), F)
                v[g[campo] == "F"] -= T * g.loc[g[campo] == "F", "votos"] / F
                v[g[campo] == "L"] += T * g.loc[g[campo] == "L", "votos"] / L
            top = v.sort_values(ascending=False).index[:vagas]
            return (g.loc[top, campo] == "L").sum()

        base = eleitos(0.0)
        if base == vagas:
            necessario = np.nan  # campo de Lula já leva as duas vagas
        else:
            lo, hi = 0.0, 0.60
            if eleitos(hi) == base:
                necessario = np.inf
            else:
                for _ in range(60):
                    mid = (lo + hi) / 2
                    if eleitos(mid) > base:
                        hi = mid
                    else:
                        lo = mid
                necessario = hi
        g_sorted = g.sort_values("votos", ascending=False)
        rows.append(dict(cenario=nome, uf=uf, vagas_L_reais=int(base),
                         swing_real_pp=round(sw.loc[uf, "swing"] * 100, 2),
                         swing_necessario_pp=round(necessario * 100, 2) if np.isfinite(necessario) else necessario,
                         eleitos=" / ".join(g_sorted[g_sorted.eleito.astype(str) == "True"].candidato),
                         ))
m = pd.DataFrame(rows)
m["folga_pp"] = m.swing_necessario_pp - m.swing_real_pp
m.to_csv(RES / "senado_swing_necessario.csv", index=False)
for nome, gg in m.groupby("cenario"):
    print("==", nome)
    print(gg.sort_values("folga_pp").head(10).to_string(index=False))
