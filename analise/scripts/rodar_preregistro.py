"""Análise pré-registrada (motor v4). Roda tudo o que o pré-registro descreve e grava em results4/.

Trava: só roda depois do registro no OSF. Crie preregistro/OSF_REGISTRADO.txt com o link do registro
(https://osf.io/...) antes de rodar. A trava existe para que nenhum resultado seja visto antes do registro.

Uso:
  python3 -I scripts/rodar_preregistro.py            # tudo (bootstrap com B = 200)
  python3 -I scripts/rodar_preregistro.py --fumaca   # teste de fumaça com fluxos embaralhados (não vale como resultado)
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor_v4 as mv  # noqa: E402

ROOT = mv.ROOT
OUT = ROOT / "results4"
LOCK = ROOT / "preregistro" / "OSF_REGISTRADO.txt"
KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]
BRACOS = ("L", "F", "comum", "total")
LAMS = [round(x, 1) for x in np.arange(0, 1.01, 0.1)]
LAMS_BOOT = [0.0, 0.25, 0.5, 0.75, 1.0]
RELEVANTE = 10          # cadeiras: limiar substantivo de mudança relevante (cerca de 2% da Câmara)
SD_RUIDO = 0.01         # piso de ruído principal: 1% nos votos das listas
H2_FAIXA = (0.40, 0.60)
H4_MARGEM = 0.02        # 2% dos votos válidos para o Senado na UF
BLOCOS = ("PL", "colig", "cdir", "cdem")
FUMACA = False


def prep(M):
    """No teste de fumaça, embaralha os fluxos com fatores aleatórios: os números perdem o sentido de propósito."""
    if not FUMACA:
        return M
    rng = np.random.default_rng(99)
    fat = {}
    for uf in M:
        n = M[uf]["n"]
        for k in n:
            fat.setdefault(k, rng.uniform(0.5, 1.5))
        M[uf]["n"] = {k: v * fat[k] for k, v in n.items()}
    return M


def cfg(braco, C=True, lam=0.0, **kw):
    return {"C": C, "lam_P": lam, "arms": mv.ARMS if braco == "total" else (braco,), **kw}


def cadeiras(r):
    return {k: r[k] for k in BLOCOS + ("sen_L", "sen_F", "sen_N")}


def efeito(r, plac):
    return {f"ef_{k}": r[k] - plac[k] for k in BLOCOS}


# ---------------- bootstrap: gera as reamostragens que faltarem ----------------
def gera_boot(b):
    eo = ROOT / "results2_n0_boot" / f"b{b}"
    if (eo / "perfis_calibrados.csv").exists():
        return b
    mz = ROOT / "munzona"
    files = {f: pd.read_csv(mz / f) for f in ["pres_munzona.csv", "dep_munzona.csv", "sen_munzona.csv", "legis_detalhe_munzona.csv"]}
    rng = np.random.default_rng(1000 + b)
    keys = []
    for uf, g in files["pres_munzona.csv"].groupby("SG_UF"):
        k = g[KEY].values
        pick = k[rng.integers(0, len(k), len(k))]
        keys.append(pd.DataFrame(pick, columns=KEY).assign(NEW=np.arange(len(pick))))
    kk = pd.concat(keys)
    mzb = ROOT / "review" / "boot" / f"b{b}" / "mz"
    mzb.mkdir(parents=True, exist_ok=True)
    for f, df in files.items():
        m = kk.merge(df, on=KEY, how="inner")
        m["CD_MUNICIPIO"] = 0
        m["NR_ZONA"] = m.pop("NEW")
        m.to_csv(mzb / f, index=False)
    py = sys.executable
    subprocess.run([py, str(ROOT / "scripts/ei.py"), str(mzb), str(eo), "20"], check=True, capture_output=True)
    subprocess.run([py, str(ROOT / "scripts/cf.py"), str(eo), str(ROOT / "data"), str(mz), str(ROOT / "results")],
                   check=True, capture_output=True)
    return b


def roda_boot(b):
    M = prep(mv.carregar(pasta=f"boot/b{b}"))
    rows = []
    plac = {br: mv.run_v4(cfg(br, placebo=True), M) for br in BRACOS}
    for br in BRACOS:
        for lam in LAMS_BOOT:
            r = mv.run_v4(cfg(br, lam=lam), M)
            rows.append({"b": b, "braco": br, "lam": lam, **cadeiras(r), **efeito(r, plac[br])})
    m = M
    h2 = {}
    for i, nome in ((0, "lula"), (1, "flavio")):
        w = np.array([mv.ST[uf]["rows"][i] for uf in mv.UFS])
        f = np.array([m[uf]["P"][i][[mv.ICD, mv.ICM]].sum() / (1 - m[uf]["P"][i][mv.IBN]) for uf in mv.UFS])
        h2[f"h2_{nome}"] = float((w * f).sum() / w.sum())
    for r in rows:
        r.update(h2)
    return rows


# ---------------- decisões ----------------
def relevante(row):
    return max(abs(row["ef_PL"]), abs(row["ef_colig"])) >= RELEVANTE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=200)
    ap.add_argument("--proc", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--fumaca", action="store_true")
    a = ap.parse_args()
    global FUMACA, OUT
    if a.fumaca:
        FUMACA, OUT, a.B = True, ROOT / "results4_fumaca", 2
    elif not LOCK.exists() or "osf.io" not in LOCK.read_text():
        sys.exit("Trava ativa: registre o pré-registro no OSF e grave o link em preregistro/OSF_REGISTRADO.txt.")
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    M = prep(mv.carregar(20))
    real = cadeiras(mv.run_v4({}, M))

    # 1. principal: canal C por braço, placebo e curva de arrasto (C + P(lam))
    plac = {br: mv.run_v4(cfg(br, placebo=True), M) for br in BRACOS}
    prin = []
    for br in BRACOS:
        prin.append({"braco": br, "config": "placebo_C", "lam": 0.0, **cadeiras(plac[br])})
        for lam in LAMS:
            r = mv.run_v4(cfg(br, lam=lam), M)
            prin.append({"braco": br, "config": "C+P", "lam": lam, **cadeiras(r), **efeito(r, plac[br]), "sen_flips": r["sen_flips"]})
    prin = pd.DataFrame(prin)
    prin.to_csv(OUT / "principal.csv", index=False)

    # 2. clima (só limites)
    cli = []
    for tau in (0.05, 0.10, 0.20):
        for br, par in (("L", {"tau_L": tau}), ("F", {"tau_F": tau}), ("total", {"tau_L": tau, "tau_F": tau})):
            r = mv.run_v4({**cfg(br, C=False), "clima": True, **par}, M)
            cli.append({"braco": br, "tau": tau, **cadeiras(r), **{f"d_{k}": r[k] - real[k] for k in BLOCOS}})
    pd.DataFrame(cli).to_csv(OUT / "clima.csv", index=False)

    # 3. sensibilidade, um fator por vez, em lam = 0, 0.5 e 1
    variantes = [("base", {}, 20)]
    variantes += [(f"alpha={v}", {"alpha_L": v, "alpha_F": v}, 20) for v in (-1.0, -0.5, 0.5, 1.0)]
    variantes += [("alpha_L=+0.5 só", {"alpha_L": 0.5}, 20), ("alpha_F=+0.5 só", {"alpha_F": 0.5}, 20)]
    variantes += [(f"rho={v}", {"rho": v}, 20) for v in (0.1, 0.2)]
    variantes += [(f"mu=nu={v}", {"mu": v, "nu": v}, 20) for v in (0.5, 1.0)]
    variantes += [("geo", {"geo": 1}, 20), ("sem saídas", {"saidas": False}, 20)]
    variantes += [("mec=nenhum", {"mec": "nenhum"}, 20), ("mec=datafolha", {"mec": "datafolha"}, 20)]
    variantes += [("n0=0", {}, 0), ("n0=100", {}, 100), ("modelo contextual", {}, "ext"), ("modelo ordinal", {}, "ord")]
    modelos = {20: M}
    sens = []
    for nome, par, mod in variantes:
        if mod not in modelos:
            modelos[mod] = prep(mv.carregar(pasta=mod) if isinstance(mod, str) else mv.carregar(mod))
        Mm = modelos[mod]
        for br in ("L", "F", "total"):
            pl = mv.run_v4({**cfg(br, placebo=True), **par}, Mm)
            for lam in (0.0, 0.5, 1.0):
                r = mv.run_v4({**cfg(br, lam=lam), **par}, Mm)
                sens.append({"variante": nome, "braco": br, "lam": lam, **cadeiras(r), **efeito(r, pl)})
    pd.DataFrame(sens).to_csv(OUT / "sensibilidade.csv", index=False)

    # 4. piso de ruído
    ru = []
    for sd in (0.005, 0.01, 0.02):
        for i, r in enumerate(mv.ruido(M, sd, 5 if FUMACA else 200, seed=2026)):
            ru.append({"sd": sd, "draw": i, **r})
    ru = pd.DataFrame(ru)
    ru.to_csv(OUT / "ruido.csv", index=False)
    p95 = {k: float(ru[ru.sd == SD_RUIDO][k].abs().quantile(0.95)) for k in BLOCOS}

    # 5. bootstrap
    with Pool(a.proc) as pool:
        if not FUMACA:
            list(pool.imap_unordered(gera_boot, range(a.B)))
        bo = sum(pool.map(roda_boot, range(a.B)), [])
    bo = pd.DataFrame(bo)
    bo.to_csv(OUT / "bootstrap.csv", index=False)

    # 6. hipóteses
    def ic(df, col):
        return float(df[col].quantile(0.025)), float(df[col].quantile(0.975))

    dec = []
    # H1
    h1 = []
    for br in BRACOS:
        pt = prin[(prin.braco == br) & (prin.config == "C+P") & (prin.lam == 0.0)].iloc[0]
        bb = bo[(bo.braco == br) & (bo.lam == 0.0)]
        dentro = all(abs(pt[f"ef_{k}"]) <= max(p95[k], 0) for k in ("PL", "colig"))
        fora = any((ic(bb, f"ef_{k}")[0] > p95[k]) or (ic(bb, f"ef_{k}")[1] < -p95[k]) for k in ("PL", "colig"))
        h1.append("apoiada" if dentro and not fora else ("refutada" if fora else "inconclusiva"))
        dec.append({"hipotese": "H1", "braco": br, "ef_PL": pt.ef_PL, "ef_colig": pt.ef_colig,
                    "ic_PL": ic(bb, "ef_PL"), "ic_colig": ic(bb, "ef_colig"), "p95_ruido": (p95["PL"], p95["colig"]), "resultado": h1[-1]})
    # H2
    for nome in ("lula", "flavio"):
        lo, hi = ic(bo.drop_duplicates("b"), f"h2_{nome}")
        res = "apoiada" if lo >= H2_FAIXA[0] and hi <= H2_FAIXA[1] else ("refutada" if hi < H2_FAIXA[0] or lo > H2_FAIXA[1] else "inconclusiva")
        dec.append({"hipotese": "H2", "braco": nome, "ic": (lo, hi), "faixa": H2_FAIXA, "resultado": res,
                    "nota": "descritiva; o valor nacional já tinha sido visto antes do registro"})
    # H3
    for br in BRACOS:
        cur = prin[(prin.braco == br) & (prin.config == "C+P")].sort_values("lam")
        rel = cur[cur.apply(relevante, axis=1)]
        lam_star = float(rel.lam.min()) if len(rel) else None
        bb = bo[bo.braco == br]
        ls = []
        for b, g in bb.groupby("b"):
            r = g[g.apply(relevante, axis=1)]
            ls.append(float(r.lam.min()) if len(r) else np.nan)
        ls = np.array(ls)
        if lam_star == 0.0:
            res = "refutada (o comparecimento sozinho já muda)"
        elif lam_star is None:
            res = "refutada (nem o arrasto total muda)"
        else:
            res = "apoiada"
        dec.append({"hipotese": "H3", "braco": br, "lam_estrela": lam_star,
                    "boot_lam_estrela_mediana": float(np.nanmedian(ls)) if np.isfinite(ls).any() else None,
                    "boot_sem_mudanca": float(np.isnan(ls).mean()), "resultado": res})
    # H4
    real_marg = {}
    for uf in mv.UFS:
        s = mv.ST[uf]
        v = np.sort(s["sen_v"])[::-1]
        real_marg[uf] = (v[1] - v[2]) / s["sen_v"].sum()
    for lam in (0.0, 1.0):
        r = prin[(prin.braco == "total") & (prin.config == "C+P") & (prin.lam == lam)].iloc[0]
        ufs = [x.split(":")[0] for x in str(r.sen_flips).split("; ") if ":" in x]
        ok = all(real_marg[u] < H4_MARGEM for u in ufs)
        dec.append({"hipotese": "H4", "braco": "total", "lam": lam, "trocas": r.sen_flips,
                    "margens_reais": {u: round(real_marg[u], 4) for u in ufs}, "resultado": "apoiada" if ok else "refutada"})
    pd.DataFrame(dec).to_json(OUT / "hipoteses.json", orient="records", force_ascii=False, indent=1)

    # 7. manifesto
    def h(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    man = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0)), "duracao_s": round(time.time() - t0),
           "osf": "teste de fumaça" if FUMACA else LOCK.read_text().strip(), "B": a.B, "python": platform.python_version(),
           "pacotes": {m: __import__(m).__version__ for m in ("numpy", "pandas", "cvxpy")},
           "codigo": {f: h(ROOT / "scripts" / f) for f in ("motor_v4.py", "rodar_preregistro.py", "behaviors.py", "ei.py", "cf.py", "seats.py")},
           "real": real, "p95_ruido": p95, "limiar_relevante": RELEVANTE}
    (OUT / "manifesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print(f"pronto em {man['duracao_s']} s; resultados em {OUT}")


if __name__ == "__main__":
    main()
