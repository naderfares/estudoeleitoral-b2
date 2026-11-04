"""Teste de b4_validar.py com dados sintéticos: uma "inferência" e um survey gerados das mesmas tabelas não podem
gerar alerta; um survey com um fluxo que a inferência põe em zero, ou com um perfil 15 pontos diferente, tem de gerar.

Uso: python3 -I scripts/teste_b4.py
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b4_validar import BLOCOS, DEST_T, ORIG_L, ORIG_T, compara  # noqa: E402

rng = np.random.default_rng(5)
F = np.array([[.97, 0, .01, .02], [0, .97, .01, .02], [.4, .45, .14, .01], [.8, 0, .19, .01], [.05, .02, .03, .90]])
P = np.array([[.05, .44, .2, .26, .05], [.41, .05, .25, .24, .05], [.2, .15, .3, .3, .05], [.1, .1, .1, .1, .6]])
tam = np.array([50e6, 52e6, 9e6, 6e6, 33e6])


def ei_dir(d):
    fl, pc = [], []
    for uf, f in (("AA", .4), ("BB", .6)):
        for i, o in enumerate(ORIG_T):
            for j, de in enumerate(DEST_T):
                fl.append({"uf": uf, "origem": o, "destino": de, "taxa_ei": F[i, j], "votos": tam[i] * f * F[i, j]})
        for i, o in enumerate(ORIG_L):
            pc.append({"": o, **dict(zip(BLOCOS, P[i])), "uf": uf, "cargo": "deputado"})
    pd.DataFrame(fl).to_csv(d / "fluxos_por_uf.csv", index=False)
    pd.DataFrame(pc).set_index("").to_csv(d / "perfis_calibrados.csv")


def survey(Fs, Ps, n=200000):
    o = rng.choice(5, n, p=tam / tam.sum())
    d = np.array([rng.choice(4, p=Fs[i]) for i in o])
    b = np.array([rng.choice(5, p=Ps[i]) if i < 4 else -1 for i in o])
    return pd.DataFrame({"V1": o + 1, "V2": d + 1, "DEP": b + 1, "PESO": 1.0})


mapa = {"peso": "PESO",
        "voto_1t": {"variavel": "V1", "codigos": {o: [i + 1] for i, o in enumerate(ORIG_T)}},
        "voto_2t": {"variavel": "V2", "codigos": {d: [i + 1] for i, d in enumerate(DEST_T)}},
        "deputado": {"variavel": "DEP", "codigos": {b: [i + 1] for i, b in enumerate(BLOCOS)}}}
d = Path(tempfile.mkdtemp())
ei_dir(d)
falhas = []
_, _, _, _, al, h2 = compara(survey(F, P), mapa, d)
print(("ok    " if not al else "FALHA ") + f"survey das mesmas tabelas: {len(al)} alerta(s)")
falhas += ["sem alerta"] if al else []
F2 = F.copy(); F2[0] = [.92, .05, .01, .02]
_, _, _, _, al, _ = compara(survey(F2, P), mapa, d)
ok = any("lula1 -> flavio2" in x for x in al)
print(("ok    " if ok else "FALHA ") + "fluxo que a inferência zera e o survey estima em 5% gera alerta")
falhas += [] if ok else ["alerta de fluxo"]
P2 = P.copy(); P2[1] = [.26, .05, .40, .24, .05]
_, _, _, _, al, _ = compara(survey(F, P2), mapa, d)
ok = any("perfil flavio1 -> PL" in x for x in al)
print(("ok    " if ok else "FALHA ") + "perfil 15 pontos diferente gera alerta")
falhas += [] if ok else ["alerta de perfil"]
ok = abs(h2["h2_lula_eseb"] - h2["h2_lula_inferencia"]) < 0.01
print(("ok    " if ok else "FALHA ") + "índice de H2 do survey bate com o da inferência quando as tabelas são iguais")
falhas += [] if ok else ["h2"]
print("todos os testes passaram" if not falhas else "FALHA: " + ", ".join(falhas))
sys.exit(1 if falhas else 0)
