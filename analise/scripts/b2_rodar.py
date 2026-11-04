"""Adendo, análise B2: motor v4 com os sorteios da posteriori do modelo bayesiano R×C (ei_bayes.py).

Passos: (1) roda ei_bayes.py para todas as UFs, gravando os sorteios em results2_n0_bayes/b{k}; (2) roda o cf.py
congelado em cada sorteio, para calibrar os perfis como na análise principal; (3) para cada sorteio, calcula o
placebo e a curva de arrasto em cada braço (λ = 0; 0,25; 0,5; 0,75; 1) e o índice de H2, como no bootstrap da
análise principal; (4) compara os fluxos nacionais com os da regressão de Goodman.

Uso:
  python3 -I scripts/b2_rodar.py                     # corrida real: exige o link do adendo em preregistro/ADENDO_B2_REGISTRADO.txt
  python3 -I scripts/b2_rodar.py --fumaca --sem-inferencia --origem-sorteios results2_n0_boot --K 2
                                                     # teste de fumaça do encadeamento, com fluxos embaralhados
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor_v4 as mv  # noqa: E402
import rodar_preregistro as rp  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=int, default=200)
    ap.add_argument("--fumaca", action="store_true")
    ap.add_argument("--sem-inferencia", action="store_true", help="usa sorteios já gravados (só para teste)")
    ap.add_argument("--origem-sorteios", default="", help="no teste, pasta de onde copiar sorteios prontos")
    a, resto = ap.parse_known_args()
    R = mv.ROOT
    lock = R / "preregistro" / "ADENDO_B2_REGISTRADO.txt"
    if a.fumaca:
        rp.FUMACA, out = True, R / "results_b2_fumaca"
    elif not lock.exists() or "osf.io" not in lock.read_text():
        sys.exit("Trava ativa: registre a parte B2 do adendo no OSF e grave o link em preregistro/ADENDO_B2_REGISTRADO.txt.")
    else:
        out = R / "results_b2"
    out.mkdir(exist_ok=True)
    bay = R / "results2_n0_bayes"
    py = sys.executable

    if not a.sem_inferencia:
        subprocess.run([py, str(R / "scripts" / "ei_bayes.py"), str(R / "munzona"), str(bay), str(R / "results2_n0_20"),
                        "--sorteios", str(a.K), *resto], check=True)
    elif a.origem_sorteios:
        if not a.fumaca:
            sys.exit("--origem-sorteios só vale no teste de fumaça")
        for k in range(a.K):
            shutil.copytree(R / a.origem_sorteios / f"b{k}", bay / f"b{k}", dirs_exist_ok=True)
    for k in range(a.K):
        subprocess.run([py, str(R / "scripts" / "cf.py"), str(bay / f"b{k}"), str(R / "data"), str(R / "munzona"),
                        str(R / "results")], check=True, capture_output=True)

    linhas, nac = [], []
    for k in range(a.K):
        M = rp.prep(mv.carregar(pasta=f"bayes/b{k}"))
        plac = {br: mv.run_v4(rp.cfg(br, placebo=True), M) for br in rp.BRACOS}
        h2 = {}
        for i, nome in ((0, "lula"), (1, "flavio")):
            w = np.array([mv.ST[uf]["rows"][i] for uf in mv.UFS])
            f = np.array([M[uf]["P"][i][[mv.ICD, mv.ICM]].sum() / (1 - M[uf]["P"][i][mv.IBN]) for uf in mv.UFS])
            h2[f"h2_{nome}"] = float((w * f).sum() / w.sum())
        for br in rp.BRACOS:
            for lam in rp.LAMS_BOOT:
                r = mv.run_v4(rp.cfg(br, lam=lam), M)
                linhas.append({"k": k, "braco": br, "lam": lam, **rp.cadeiras(r), **rp.efeito(r, plac[br]), **h2})
        fl = pd.read_csv(bay / f"b{k}" / "fluxos_por_uf.csv")
        nac.append(fl.groupby(["origem", "destino"]).votos.sum().rename(k))
    pd.DataFrame(linhas).to_csv(out / "bayes.csv", index=False)

    nac = pd.concat(nac, axis=1)
    g = pd.read_csv(R / "results2_n0_20" / "fluxos_por_uf.csv").groupby(["origem", "destino"]).votos.sum()
    comp = pd.DataFrame({"goodman": g, "bayes_mediana": nac.median(1), "bayes_p2_5": nac.quantile(0.025, axis=1),
                         "bayes_p97_5": nac.quantile(0.975, axis=1)})
    comp["diferenca"] = comp.bayes_mediana - comp.goodman
    comp["discutir_no_texto"] = comp.diferenca.abs() > 1e6
    comp.to_csv(out / "comparacao_fluxos_nacionais.csv")
    if a.fumaca:
        (out / "LEIA-ME.txt").write_text("TESTE DE FUMAÇA: números sem significado.\n")
    print("pronto; saída em", out)


if __name__ == "__main__":
    main()
