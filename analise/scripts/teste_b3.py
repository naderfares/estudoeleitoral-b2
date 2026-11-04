"""Teste de b3_preparar.py: gera arquivos sintéticos no formato do TSE por seção, dividindo cada zona real em duas
seções, converte e confere que a soma das seções devolve exatamente os arquivos por zona.

Não faz nenhuma inferência: só confere a conversão de formato.
Uso: python3 -I scripts/teste_b3.py [--ufs AC,RR]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]
A = Path(__file__).resolve().parents[1]


def divide(x, f):
    a = np.floor(x * f).astype(int)
    return a, x - a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ufs", default="AC,RR")
    ufs = ap.parse_args().ufs.split(",")
    mz, data = A / "munzona", A / "data"
    pres = pd.read_csv(mz / "pres_munzona.csv")
    dep = pd.read_csv(mz / "dep_munzona.csv")
    sen = pd.read_csv(mz / "sen_munzona.csv")
    ldet = pd.read_csv(mz / "legis_detalhe_munzona.csv")
    cc = pd.read_csv(data / "camara_candidatos_2026.csv", keep_default_na=False)
    cp = pd.read_csv(data / "camara_partidos_2026.csv", keep_default_na=False)
    rng = np.random.default_rng(3)
    tmp = Path(tempfile.mkdtemp())
    ok = True
    for uf in ufs:
        # um número de candidato representativo por agremiação (os dois primeiros dígitos dão o partido)
        part_agr = cp[cp.uf == uf].groupby("agremiacao").partido.first()
        num = {}
        for ag, pa in part_agr.items():
            nums = cc[(cc.uf == uf) & (cc.partido == pa)].numero
            if len(nums):
                num[ag] = int(nums.iloc[0])
        V, D = [], []
        pu = pres[pres.SG_UF == uf]
        for r in pu.itertuples():
            f = rng.uniform(0.2, 0.8)
            for t in (1, 2):
                for col, nv in (("lula", 13), ("flavio", 22), ("outros", 12)):
                    if f"{col}{t}" not in pu.columns:
                        continue
                    a, b = divide(getattr(r, f"{col}{t}"), f)
                    V += [(uf, r.CD_MUNICIPIO, r.NR_ZONA, 1, t, 1, nv, a), (uf, r.CD_MUNICIPIO, r.NR_ZONA, 2, t, 1, nv, b)]
                vals = [getattr(r, f"{c}{t}") for c in ("aptos", "comp", "abst", "bn")]
                sp = [divide(x, f) for x in vals]
                D += [(uf, r.CD_MUNICIPIO, r.NR_ZONA, s + 1, t, 1, *[sp[i][s] for i in range(3)], sp[3][s], 0) for s in (0, 1)]
            # legislativo no 1º turno, com a mesma fração
            for _, q in dep[(dep.SG_UF == uf) & (dep.CD_MUNICIPIO == r.CD_MUNICIPIO) & (dep.NR_ZONA == r.NR_ZONA)].iterrows():
                if q.agremiacao not in num:
                    continue
                a, b = divide(q.votos, f)
                V += [(uf, r.CD_MUNICIPIO, r.NR_ZONA, 1, 1, 6, num[q.agremiacao], a), (uf, r.CD_MUNICIPIO, r.NR_ZONA, 2, 1, 6, num[q.agremiacao], b)]
            for _, q in sen[(sen.SG_UF == uf) & (sen.CD_MUNICIPIO == r.CD_MUNICIPIO) & (sen.NR_ZONA == r.NR_ZONA)].iterrows():
                a, b = divide(q.votos, f)
                V += [(uf, r.CD_MUNICIPIO, r.NR_ZONA, 1, 1, 5, int(q.NR_CANDIDATO), a), (uf, r.CD_MUNICIPIO, r.NR_ZONA, 2, 1, 5, int(q.NR_CANDIDATO), b)]
            for _, q in ldet[(ldet.SG_UF == uf) & (ldet.CD_MUNICIPIO == r.CD_MUNICIPIO) & (ldet.NR_ZONA == r.NR_ZONA)].iterrows():
                cs, bs = divide(q.QT_COMPARECIMENTO, f), divide(q.bn, f)
                D += [(uf, r.CD_MUNICIPIO, r.NR_ZONA, s + 1, 1, int(q.CD_CARGO), 0, cs[s], 0, bs[s], 0) for s in (0, 1)]
        pd.DataFrame(V, columns=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_TURNO", "CD_CARGO", "NR_VOTAVEL", "QT_VOTOS"]) \
            .to_csv(tmp / f"votacao_secao_2026_{uf}.csv", sep=";", index=False, encoding="latin-1")
        pd.DataFrame(D, columns=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_TURNO", "CD_CARGO", "QT_APTOS", "QT_COMPARECIMENTO",
                                 "QT_ABSTENCOES", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS"]) \
            .to_csv(tmp / f"detalhe_votacao_secao_2026_{uf}.csv", sep=";", index=False, encoding="latin-1")

    out = tmp / "saida"
    subprocess.run([sys.executable, str(A / "scripts" / "b3_preparar.py"), str(tmp), str(data), str(out), "--ufs", ",".join(ufs)],
                   check=True, capture_output=True)

    def volta(df):
        df = df.copy()
        df["NR_ZONA"] = df.NR_ZONA // 10000
        return df

    p2 = volta(pd.read_csv(out / "pres_munzona.csv")).groupby(KEY).sum().sort_index()
    p1 = pres[pres.SG_UF.isin(ufs)].set_index(KEY).sort_index()[p2.columns]
    ok &= np.allclose(p1.values, p2.values)
    print(("ok    " if ok else "FALHA ") + "presidente: seções somam as zonas")
    d2 = volta(pd.read_csv(out / "dep_munzona.csv")).groupby(KEY + ["agremiacao"]).votos.sum()
    d1 = dep[dep.SG_UF.isin(ufs)].groupby(KEY + ["agremiacao"]).votos.sum()
    pares = set(zip(d2.index.get_level_values("SG_UF"), d2.index.get_level_values("agremiacao")))
    d1 = d1[[(u, g) in pares for u, g in zip(d1.index.get_level_values("SG_UF"), d1.index.get_level_values("agremiacao"))]]
    d1 = d1.sort_index()
    okd = bool(np.allclose(d1.values, d2.reindex(d1.index).fillna(-1).values)) and len(d2) == len(d1)
    print(("ok    " if okd else "FALHA ") + "deputado: seções somam as zonas por agremiação")
    s2 = volta(pd.read_csv(out / "sen_munzona.csv")).groupby(KEY + ["NR_CANDIDATO"]).votos.sum().sort_index()
    s1 = sen[sen.SG_UF.isin(ufs)].groupby(KEY + ["NR_CANDIDATO"]).votos.sum().sort_index()
    oks = np.allclose(s1.values, s2.reindex(s1.index).values)
    print(("ok    " if oks else "FALHA ") + "senado: seções somam as zonas por candidato")
    l2 = volta(pd.read_csv(out / "legis_detalhe_munzona.csv")).groupby(KEY + ["CD_CARGO"])[["QT_COMPARECIMENTO", "bn"]].sum().sort_index()
    l1 = ldet[ldet.SG_UF.isin(ufs)].groupby(KEY + ["CD_CARGO"])[["QT_COMPARECIMENTO", "bn"]].sum().sort_index()
    okl = np.allclose(l1.values, l2.reindex(l1.index).values)
    print(("ok    " if okl else "FALHA ") + "detalhe legislativo: seções somam as zonas")
    zz = pd.read_csv(out / "pres_munzona.csv")
    oku = not zz.duplicated(KEY).any() and len(zz) == 2 * len(p1)
    print(("ok    " if oku else "FALHA ") + "cada seção vira uma unidade única")
    sys.exit(0 if (ok and okd and oks and okl and oku) else 1)


if __name__ == "__main__":
    main()
