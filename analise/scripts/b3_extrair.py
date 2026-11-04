"""Análise complementar B3 (dados por seção): separa, dos zips do TSE por seção, só as colunas e cargos que
b3_preparar.py lê, no formato que ele espera (um par de CSVs por UF).

Nos dados de 2026, os votos de presidente por seção vêm num arquivo nacional (votacao_secao_2026_BR.zip) e os de
deputado federal e senador nos arquivos de cada UF (votacao_secao_2026_UF.zip). O detalhe por seção vem num zip só
(detalhe_votacao_secao_2026.zip), com um CSV para o presidente (_BR) e um por UF. Este script junta as duas fontes
por UF. Não soma nem transforma nenhum número: só filtra linhas (cargos 1, 5 e 6; para senador e deputado, só o
1º turno) e colunas.

Uso: python3 -I b3_extrair.py PASTA_ZIPS SAIDA
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
SEC = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
CV = SEC + ["NR_TURNO", "CD_CARGO", "NR_VOTAVEL", "QT_VOTOS"]
CD = SEC + ["NR_TURNO", "CD_CARGO", "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS"]
Z, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


def le(zipname, membro, cols, filtro):
    partes = []
    with zipfile.ZipFile(Z / zipname).open(membro) as f:
        for ch in pd.read_csv(f, sep=";", encoding="latin-1", usecols=cols, chunksize=1_000_000,
                              dtype={"SG_UF": str}, low_memory=False):
            partes.append(filtro(ch))
    return pd.concat(partes, ignore_index=True)[cols]


def por_uf(df):
    return {uf: g for uf, g in df.groupby("SG_UF")}


pres_v = por_uf(le("votacao_secao_2026_BR.zip", "votacao_secao_2026_BR.csv", CV, lambda d: d[d.CD_CARGO == 1]))
pres_d = por_uf(le("detalhe_votacao_secao_2026.zip", "detalhe_votacao_secao_2026_BR.csv", CD, lambda d: d[d.CD_CARGO == 1]))
print("presidente:", sum(len(g) for g in pres_v.values()), "linhas de voto", flush=True)

for uf in UFS:
    leg = lambda d: d[d.CD_CARGO.isin([5, 6]) & (d.NR_TURNO == 1)]
    v = le(f"votacao_secao_2026_{uf}.zip", f"votacao_secao_2026_{uf}.csv", CV, leg)
    d = le("detalhe_votacao_secao_2026.zip", f"detalhe_votacao_secao_2026_{uf}.csv", CD, leg)
    pd.concat([pres_v[uf], v]).to_csv(OUT / f"votacao_secao_2026_{uf}.csv", sep=";", index=False, encoding="latin-1")
    pd.concat([pres_d[uf], d]).to_csv(OUT / f"detalhe_votacao_secao_2026_{uf}.csv", sep=";", index=False, encoding="latin-1")
    print(uf, len(pres_v[uf]) + len(v), "linhas de voto", flush=True)
print("pronto")
