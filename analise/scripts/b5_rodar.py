"""Adendo 1, análise B5: curva de arrasto separada para UFs com e sem 2º turno para governador.

Usa o motor v4 congelado sem alteração. As cadeiras da Câmara são distribuídas dentro de cada UF, então o efeito
de um grupo de UFs é a soma dos efeitos das suas UFs: basta rodar o motor com a lista de UFs restrita ao grupo.
O Senado também é decidido por UF. A incerteza vem das mesmas reamostragens do bootstrap da análise principal.

Lista de UFs com 2º turno para governador em 25/10/2026 (padrão): AC, AM, DF, ES, RN, TO. A lista precisa ser
conferida nos resultados oficiais do TSE antes do registro do adendo.

Uso:
  python3 -I scripts/b5_rodar.py                 # corrida real: exige o link do adendo em preregistro/ADENDO1_REGISTRADO.txt
  python3 -I scripts/b5_rodar.py --fumaca        # teste de fumaça com fluxos embaralhados e 2 reamostragens
  python3 -I scripts/b5_rodar.py --ufs AC,AM,... # outra lista de UFs com 2º turno para governador
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor_v4 as mv  # noqa: E402
import rodar_preregistro as rp  # noqa: E402

PADRAO = "AC,AM,DF,ES,RN,TO"
LAMS = [round(x, 1) for x in np.arange(0, 1.01, 0.1)]
LAMS_BOOT = [0.0, 0.25, 0.5, 0.75, 1.0]


def curva(M, ufs, lams):
    todas = mv.UFS
    mv.UFS = [u for u in todas if u in ufs]
    try:
        out = []
        for br in rp.BRACOS:
            pl = mv.run_v4(rp.cfg(br, placebo=True), M)
            for lam in lams:
                r = mv.run_v4(rp.cfg(br, lam=lam), M)
                out.append({"braco": br, "lam": lam, **rp.cadeiras(r), **rp.efeito(r, pl), "sen_flips": r["sen_flips"]})
        return out
    finally:
        mv.UFS = todas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ufs", default=PADRAO)
    ap.add_argument("--B", type=int, default=200)
    ap.add_argument("--fumaca", action="store_true")
    a = ap.parse_args()
    lock = mv.ROOT / "preregistro" / "ADENDO1_REGISTRADO.txt"
    if a.fumaca:
        rp.FUMACA, out, a.B = True, mv.ROOT / "results_b5_fumaca", 2
    elif not lock.exists() or "osf.io" not in lock.read_text():
        sys.exit("Trava ativa: registre o adendo 1 no OSF e grave o link em preregistro/ADENDO1_REGISTRADO.txt.")
    else:
        out = mv.ROOT / "results_b5"
    out.mkdir(exist_ok=True)
    com = set(a.ufs.split(","))
    assert com <= set(mv.UFS), "UF desconhecida na lista"
    grupos = {"com 2º turno para governador": com, "sem 2º turno para governador": set(mv.UFS) - com}

    M = rp.prep(mv.carregar(20))
    linhas = []
    for g, ufs in grupos.items():
        linhas += [{"grupo": g, **r} for r in curva(M, ufs, LAMS)]
    pd.DataFrame(linhas).to_csv(out / "curva_por_grupo.csv", index=False)

    boot = []
    for b in range(a.B):
        Mb = rp.prep(mv.carregar(pasta=f"boot/b{b}"))
        for g, ufs in grupos.items():
            boot += [{"b": b, "grupo": g, **r} for r in curva(Mb, ufs, LAMS_BOOT)]
    pd.DataFrame(boot).to_csv(out / "bootstrap_por_grupo.csv", index=False)
    (out / "LEIA-ME.txt").write_text(f"UFs com 2º turno para governador: {', '.join(sorted(com))}\n"
                                     + ("TESTE DE FUMAÇA: números sem significado.\n" if a.fumaca else ""))
    print("pronto; saída em", out)


if __name__ == "__main__":
    main()
