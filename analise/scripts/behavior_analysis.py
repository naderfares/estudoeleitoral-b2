"""Bateria de testes de comportamento: um fator por vez, cenários nomeados, Monte Carlo e ponto de virada."""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import behaviors as B  # noqa: E402

OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
NMC = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
models = {n0: B.load_model(n0) for n0 in (0, 20, 100)}


def run(par):
    p = {**B.BASE, **par}
    return B.run(p, models[p["n0"]])


# valores reais
real = dict(PL=121, PT=70, colig=124, outros=268)
sr = pd.read_csv(B.DATA / "senado_candidatos_2026.csv", keep_default_na=False)
sr = sr[sr.eleito.astype(str) == "True"]
camp = [B.campo_sen.get((r.uf, str(r.numero)), "N") for r in sr.itertuples()]
real.update(sen_L=camp.count("L"), sen_F=camp.count("F"), sen_N=camp.count("N"))
print("real:", real)

t0 = time.time()
base = run({})
print(f"base ({time.time()-t0:.2f}s):", {k: v for k, v in base.items() if k != "sen_flips"}, base["sen_flips"])

# ---------- 1) um fator por vez ----------
OAT = [
    ("alpha_L", -1.0, "Mobilizados pró-Lula votam como o eleitor médio da UF (sem viés de esquerda)"),
    ("alpha_L", -0.5, "Mobilizados pró-Lula: metade do caminho até o eleitor médio"),
    ("alpha_L", 0.5, "Mobilizados pró-Lula bem mais à esquerda que o eleitor típico de Lula"),
    ("alpha_L", 1.0, "Mobilizados pró-Lula: 100% dos votos válidos na coligação de Lula (extremo)"),
    ("rho", 0.3, "30% dos mobilizados só votam para presidente (branco no Legislativo)"),
    ("rho", 0.6, "60% dos mobilizados só votam para presidente"),
    ("alpha_F", -1.0, "Mobilizados pró-Flávio votam como o eleitor médio da UF"),
    ("alpha_F", 1.0, "Mobilizados pró-Flávio: 100% dos votos válidos no PL/campo de Flávio"),
    ("geo", 1, "Mobilizados votam como os vizinhos de mesma escolha nas zonas onde o comparecimento cresceu"),
    ("lam_O", 0.5, "Eleitores dos outros presidenciáveis: metade adota o perfil legislativo da escolha do 2º turno"),
    ("lam_O", 1.0, "Eleitores dos outros presidenciáveis: todos adotam (arrasto total)"),
    ("lam_BN", 0.5, "Metade dos branco/nulo do 1º turno que foram a Lula/Flávio muda o voto legislativo"),
    ("lam_BN", 1.0, "Todos os branco/nulo do 1º turno que foram a Lula/Flávio mudam o voto legislativo"),
    ("mu", 0.5, "Metade do fluxo branco/nulo -> Lula era, na verdade, abstenção -> Lula (mais mobilização)"),
    ("mu", 1.0, "Todo o fluxo branco/nulo -> Lula era abstenção -> Lula (mobilização máxima: +4,2 mi)"),
    ("nu", 0.5, "Metade do fluxo outros presidenciáveis -> Lula era, na verdade, abstenção -> Lula"),
    ("demob", 1, "Quem votou no 1º e faltou no 2º perde o voto legislativo"),
    ("lam_S", 0.0, "Quem trocou Flávio <-> Lula mantém o voto legislativo"),
    ("kappa", 1.0, "Ganho da esquerda vai todo para a federação PT/PCdoB/PV"),
    ("tau_L", 0.10, "Efeito clima: 10% do voto de centro dos eleitores fiéis de Lula migra para a esquerda"),
    ("tau_L", 0.25, "Efeito clima forte: 25% do voto de centro dos fiéis de Lula migra para a esquerda"),
    ("tau_F", 0.10, "Efeito clima: 10% do voto de centro dos fiéis de Flávio migra para o PL"),
    ("n0", 0, "Sem âncora estatística (N0 = 0)"),
    ("n0", 100, "Âncora forte (N0 = 100)"),
]
rows = [dict(grupo="caso-base", parametro="-", valor="-", descricao="Cenário principal da versão 2", **base)]
for par, val, desc in OAT:
    r = run({par: val})
    rows.append(dict(grupo="um fator por vez", parametro=par, valor=val, descricao=desc, **r))
    print(f"{par}={val}: PL {r['PL']} colig {r['colig']} sen L/F/N {r['sen_L']}/{r['sen_F']}/{r['sen_N']} | {r['sen_flips']}")

# ---------- 2) cenários nomeados (combinações) ----------
NOMEADOS = [
    ("Neutro: mobilizados sem viés partidário",
     dict(alpha_L=-1, alpha_F=-1)),
    ("Esquerda forte: mobilizados mais à esquerda + geografia + PT-cêntrico",
     dict(alpha_L=0.5, geo=1, kappa=1)),
    ("Onda pró-Lula plausível: esquerda forte + metade do arrasto e mais mobilização",
     dict(alpha_L=0.5, geo=1, kappa=0.5, lam_O=0.5, lam_BN=0.5, mu=0.5)),
    ("Teto absoluto pró-esquerda: tudo no máximo a favor da esquerda",
     dict(alpha_L=1, alpha_F=-1, geo=1, kappa=1, lam_O=1, lam_BN=1, mu=1, rho=0, n0=0)),
    ("Polarização dos dois lados (clima 10% para Lula e para Flávio)",
     dict(tau_L=0.10, tau_F=0.10)),
    ("Polarização só à esquerda (clima 25% Lula) + onda pró-Lula plausível",
     dict(tau_L=0.25, alpha_L=0.5, geo=1, kappa=0.5, lam_O=0.5, lam_BN=0.5, mu=0.5)),
    ("Só foram votar para presidente: 60% de roll-off",
     dict(rho=0.6)),
    ("Desfavorável à esquerda: mobilizados neutros, pró-Flávio militantes, desmobilização conta",
     dict(alpha_L=-1, alpha_F=1, demob=1)),
]
for nome, par in NOMEADOS:
    r = run(par)
    rows.append(dict(grupo="cenário combinado", parametro="; ".join(f"{k}={v}" for k, v in par.items()), valor="-", descricao=nome, **r))
    print(f"[{nome}] PL {r['PL']} colig {r['colig']} PT {r['PT']} sen L/F/N {r['sen_L']}/{r['sen_F']}/{r['sen_N']} RJ {r['RJ_jordy_menos_benedita']:.0f} | {r['sen_flips']}")
tab = pd.DataFrame(rows)
tab.to_csv(OUT / "sensibilidade_comportamentos.csv", index=False)

# ---------- 3) ponto de virada: inclinação dos mobilizados ----------
pv = []
for contexto, extra in (("demais hipóteses no caso-base", {}),
                        ("com mobilização máxima (mu=1) e geografia", dict(mu=1, geo=1)),
                        ("com tudo o mais a favor da esquerda", dict(mu=1, geo=1, lam_O=1, lam_BN=1, kappa=1, alpha_F=-1))):
    for a in np.round(np.arange(-1, 1.01, 0.25), 2):
        r = run({**extra, "alpha_L": float(a)})
        pv.append(dict(contexto=contexto, alpha_L=float(a), **{k: r[k] for k in ("PL", "PT", "colig", "outros", "sen_L", "sen_F", "sen_N", "RJ_jordy_menos_benedita", "sen_flips")}))
pv = pd.DataFrame(pv)
pv.to_csv(OUT / "ponto_de_virada.csv", index=False)
print(pv[["contexto", "alpha_L", "PL", "colig", "sen_L", "sen_F", "RJ_jordy_menos_benedita"]].to_string(index=False))

# ---------- 4) Monte Carlo em faixas plausíveis ----------
rng = np.random.default_rng(2026)
mc = []
t0 = time.time()
for i in range(NMC):
    par = dict(alpha_L=rng.uniform(-1, 0.6), rho=rng.uniform(0, 0.3), alpha_F=rng.uniform(-1, 0.6),
               geo=int(rng.random() < 0.5), lam_O=rng.uniform(0, 0.5), lam_BN=rng.uniform(0, 0.5),
               mu=rng.uniform(0, 0.5), nu=rng.uniform(0, 0.5), demob=int(rng.random() < 0.2), lam_S=rng.uniform(0, 1),
               kappa=rng.uniform(0, 0.5), n0=int(rng.choice([0, 20, 100])))
    r = run(par)
    mc.append({**par, **r})
    if i == 49:
        print(f"MC: ~{(time.time()-t0)/50*NMC/60:.1f} min estimados", flush=True)
mc = pd.DataFrame(mc)
mc.to_csv(OUT / "monte_carlo.csv", index=False)
q = mc[["PL", "PT", "colig", "outros", "sen_L", "sen_F", "sen_N", "RJ_jordy_menos_benedita"]].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).T
q["min"] = mc[q.index].min()
q["max"] = mc[q.index].max()
print(q.round(0).to_string())
fl = mc.sen_flips.str.split("; ").explode().value_counts() / len(mc) * 100
print("\nFrequência de cada troca no Senado (% dos sorteios):"); print(fl.round(1).to_string())
fl.rename("pct").to_csv(OUT / "monte_carlo_senado_trocas.csv")
# correlação parâmetro x resultado (o que mais pesa)
imp = {}
for par in ("alpha_L", "rho", "alpha_F", "geo", "lam_O", "lam_BN", "mu", "nu", "demob", "lam_S", "kappa", "n0"):
    imp[par] = {k: np.corrcoef(mc[par], mc[k])[0, 1] for k in ("PL", "colig", "outros")}
imp = pd.DataFrame(imp).T
imp.to_csv(OUT / "monte_carlo_importancia.csv")
print("\nCorrelação parâmetro x cadeiras:"); print(imp.round(2).to_string())
pd.Series(real).to_csv(OUT / "real.csv")
