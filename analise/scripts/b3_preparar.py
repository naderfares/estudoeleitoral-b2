"""Adendo, análise B3: converte os arquivos do TSE por seção eleitoral no formato que ei.py e ei_bayes.py leem.

A unidade passa a ser a seção. Para não mexer no código congelado, cada seção vira uma "zona" com número composto
(NR_ZONA * 10000 + NR_SECAO), de modo que a chave (SG_UF, CD_MUNICIPIO, NR_ZONA) continue única. A saída tem os
mesmos quatro arquivos de munzona/ (pres_munzona.csv, dep_munzona.csv, sen_munzona.csv, legis_detalhe_munzona.csv)
e pode ser usada como raiz alternativa, como em B1.

Entrada: uma pasta com os CSVs do TSE já descompactados, um par por UF:
  votacao_secao_2026_{UF}.csv          colunas: SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO, NR_TURNO, CD_CARGO, NR_VOTAVEL, QT_VOTOS
  detalhe_votacao_secao_2026_{UF}.csv  colunas: SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO, NR_TURNO, CD_CARGO, QT_APTOS,
                                       QT_COMPARECIMENTO, QT_ABSTENCOES, QT_VOTOS_BRANCOS e QT_VOTOS_NULOS (ou QT_TOTAL_VOTOS_NULOS)
Os nomes seguem o padrão dos arquivos por seção de eleições anteriores; se o TSE mudar algum, o script para e
lista o que falta. Números de votável: 95 = branco, 96 = nulo, 97 = anulado sob judice (tratado como nulo). Para
deputado, os dois primeiros dígitos do número são o partido; o partido vira agremiação pela tabela da API.

Uso: python3 -I scripts/b3_preparar.py PASTA_SECOES DATA SAIDA [--ufs AC,AL]

Correção de 04/11/2026, feita ao comparar a conversão com os arquivos por zona nos dados reais (antes de rodar
qualquer inferência por seção): (1) os arquivos por seção trazem também os votos de candidatos com votação anulada
(anulado ou anulado sub judice), que nos arquivos por zona contam como nulos; agora esses votos vão para branco/nulo,
usando a situação de cada candidato nos CSVs da API (destino_voto); no detalhe de deputado e senador, como nos arquivos por zona, a
anulação definitiva e candidato fora da lista contam como nulo e a sub judice fica fora dos válidos e dos nulos; (2) votos de legenda de um partido federado sem
candidatos na UF ficavam sem agremiação; agora o número do partido vem de uma tabela nacional (os dois primeiros
dígitos dos candidatos de todas as UFs), e a legenda de partido sem lista válida na UF (sem votos de legenda na totalização oficial) conta como nulo, como nos arquivos
por zona. Depois da correção, presidente, Senado, comparecimento e votos de deputado por agremiação somam exatamente o
que está nos arquivos por zona; ver b3_conferir.py.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]
SEC = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
BRANCO_NULO = {95, 96, 97}
COL_V = SEC + ["NR_TURNO", "CD_CARGO", "NR_VOTAVEL", "QT_VOTOS"]
COL_D = SEC + ["NR_TURNO", "CD_CARGO", "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "QT_VOTOS_BRANCOS"]


def le(caminho, precisa):
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", low_memory=False)
    if "QT_TOTAL_VOTOS_NULOS" in df.columns and "QT_VOTOS_NULOS" not in df.columns:
        df = df.rename(columns={"QT_TOTAL_VOTOS_NULOS": "QT_VOTOS_NULOS"})
    falta = [c for c in precisa if c not in df.columns]
    if falta:
        sys.exit(f"{caminho.name}: faltam as colunas {falta}")
    df["CD_MUNICIPIO"] = df.CD_MUNICIPIO.astype(int)
    return df


def unidade(df):
    df = df.copy()
    df["NR_ZONA"] = df.NR_ZONA.astype(int) * 10000 + df.NR_SECAO.astype(int)
    return df.drop(columns="NR_SECAO")


def converte(pasta, data, ufs):
    cp = pd.read_csv(data / "camara_partidos_2026.csv", keep_default_na=False)
    cc = pd.read_csv(data / "camara_candidatos_2026.csv", keep_default_na=False)
    sa = pd.read_csv(data / "senado_candidatos_2026.csv", keep_default_na=False)
    pr = pd.read_csv(data / "presidente_por_uf_1t_2t.csv", keep_default_na=False)
    agr = {(r.uf, r.partido): r.agremiacao for r in cp.itertuples()}
    # legenda válida só para partidos com votos de legenda válidos na totalização oficial (lista não anulada)
    leg_ok = {(r.uf, r.partido) for r in cp.itertuples() if int(r.votos_legenda) > 0}
    num_nac = {int(str(r.numero)[:2]): r.partido for r in cc.itertuples()}
    dep_ok = {(r.uf, int(r.numero)) for r in cc.itertuples() if str(r.destino_voto).startswith("Válido")}
    sen_ok = {(r.uf, int(r.numero)) for r in sa.itertuples() if str(r.destino_voto).startswith("Válido")}
    pres_ok = {(int(r.turno), int(r.numero)) for r in pr[pr.uf == "BR"].itertuples()}
    # anulação definitiva conta como voto nulo nos arquivos por zona; a sub judice fica fora dos válidos e dos nulos
    leg_nulo = {(r.uf, 6, int(r.numero)) for r in cc.itertuples() if str(r.destino_voto) == "Anulado"}
    leg_nulo |= {(r.uf, 5, int(r.numero)) for r in sa.itertuples() if str(r.destino_voto) == "Anulado"}
    listados = {(r.uf, 6, int(r.numero)) for r in cc.itertuples()} | {(r.uf, 5, int(r.numero)) for r in sa.itertuples()}
    pres_u, dep_u, sen_u, det_u = [], [], [], []
    for uf in ufs:
        v = unidade(le(pasta / f"votacao_secao_2026_{uf}.csv", COL_V))
        d = unidade(le(pasta / f"detalhe_votacao_secao_2026_{uf}.csv", COL_D + ["QT_VOTOS_NULOS"]))
        # presidente: categorias por turno
        p = v[v.CD_CARGO == 1].copy()
        p["cat"] = p.NR_VOTAVEL.map({13: "lula", 22: "flavio"})
        invalido = ~p.NR_VOTAVEL.isin(BRANCO_NULO) & ~pd.Series(
            [(int(t), int(n)) in pres_ok for t, n in zip(p.NR_TURNO, p.NR_VOTAVEL)], index=p.index)
        anul = p[invalido].groupby(KEY + ["NR_TURNO"]).QT_VOTOS.sum()
        p.loc[p.NR_VOTAVEL.isin(BRANCO_NULO) | invalido, "cat"] = "_bn"
        p["cat"] = p.cat.fillna("outros")
        p = p[p.cat != "_bn"]
        pv = p.pivot_table(index=KEY, columns=["NR_TURNO", "cat"], values="QT_VOTOS", aggfunc="sum", fill_value=0)
        pv.columns = [f"{c}{t}" for t, c in pv.columns]
        dp = d[d.CD_CARGO == 1].copy()
        dp["bn"] = dp.QT_VOTOS_BRANCOS + dp.QT_VOTOS_NULOS
        if len(anul):
            ad = dp.set_index(KEY + ["NR_TURNO"]).index.map(anul.to_dict()).fillna(0)
            dp["bn"] = dp.bn + ad.values
        dt = dp.pivot_table(index=KEY, columns="NR_TURNO", values=["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "bn"],
                            aggfunc="sum")
        dt.columns = [{"QT_APTOS": "aptos", "QT_COMPARECIMENTO": "comp", "QT_ABSTENCOES": "abst", "bn": "bn"}[a] + str(t)
                      for a, t in dt.columns]
        pres_u.append(pv.join(dt, how="inner").reset_index())
        # deputado: votos nominais e de legenda por partido -> agremiação
        dd = v[(v.CD_CARGO == 6) & (v.NR_TURNO == 1) & ~v.NR_VOTAVEL.isin(BRANCO_NULO)].copy()
        dd["partido"] = [num_nac.get(int(str(n)[:2]), f"N{str(n)[:2]}") for n in dd.NR_VOTAVEL]
        # legenda de partido sem lista na UF conta como nulo nos arquivos por zona
        dd = dd[[((uf, p) in leg_ok) if n < 100 else ((uf, int(n)) in dep_ok) for n, p in zip(dd.NR_VOTAVEL, dd.partido)]]
        dd["agremiacao"] = [agr.get((uf, s), s) for s in dd.partido]
        dep_u.append(dd.groupby(KEY + ["agremiacao"], as_index=False).QT_VOTOS.sum().rename(columns={"QT_VOTOS": "votos"}))
        # senado: votos por candidato
        ss = v[(v.CD_CARGO == 5) & (v.NR_TURNO == 1) & ~v.NR_VOTAVEL.isin(BRANCO_NULO)]
        ss = ss[pd.Series([(uf, int(n)) in sen_ok for n in ss.NR_VOTAVEL], index=ss.index)]
        sen_u.append(ss.groupby(KEY + ["NR_VOTAVEL"], as_index=False).QT_VOTOS.sum()
                     .rename(columns={"NR_VOTAVEL": "NR_CANDIDATO", "QT_VOTOS": "votos"}))
        # detalhe dos cargos legislativos no 1º turno
        dl = d[(d.CD_CARGO.isin([5, 6])) & (d.NR_TURNO == 1)].copy()
        dl["bn"] = dl.QT_VOTOS_BRANCOS + dl.QT_VOTOS_NULOS
        leg = v[(v.CD_CARGO.isin([5, 6])) & (v.NR_TURNO == 1) & ~v.NR_VOTAVEL.isin(BRANCO_NULO)].copy()
        ok = [((uf, num_nac.get(int(n), "")) in leg_ok) if c == 6 and n < 100 else ((uf, int(n)) in (dep_ok if c == 6 else sen_ok))
              for c, n in zip(leg.CD_CARGO, leg.NR_VOTAVEL)]
        leg["ok"] = ok
        val = leg[leg.ok].groupby(KEY + ["CD_CARGO"]).QT_VOTOS.sum().rename("QT_TOTAL_VOTOS_VALIDOS")
        # como nos arquivos por zona: anulação definitiva vai para branco/nulo, a sub judice não entra em nenhum dos dois
        # candidato fora da lista da API (registro indeferido) também conta como nulo nos arquivos por zona
        leg["nulo"] = [(uf, int(c), int(n)) in leg_nulo or ((int(c) == 5 or n >= 100) and (uf, int(c), int(n)) not in listados)
                       or (int(c) == 6 and n < 100 and (uf, num_nac.get(int(n), "")) not in leg_ok)
                       for c, n in zip(leg.CD_CARGO, leg.NR_VOTAVEL)]
        anl = leg[leg.nulo].groupby(KEY + ["CD_CARGO"]).QT_VOTOS.sum().rename("anulados")
        g = dl.groupby(KEY + ["CD_CARGO"])[["QT_COMPARECIMENTO", "bn"]].sum().join(val).join(anl).fillna(0)
        g["bn"] = g.bn + g.anulados
        det_u.append(g.drop(columns="anulados").reset_index())
        print(uf, "ok", flush=True)
    return (pd.concat(pres_u, ignore_index=True).fillna(0), pd.concat(dep_u, ignore_index=True),
            pd.concat(sen_u, ignore_index=True), pd.concat(det_u, ignore_index=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", type=Path)
    ap.add_argument("data", type=Path)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--ufs", default=",".join(UFS))
    a = ap.parse_args()
    pres, dep, sen, det = converte(a.pasta, a.data, a.ufs.split(","))
    a.saida.mkdir(parents=True, exist_ok=True)
    pres.to_csv(a.saida / "pres_munzona.csv", index=False)
    dep.to_csv(a.saida / "dep_munzona.csv", index=False)
    sen.to_csv(a.saida / "sen_munzona.csv", index=False)
    det.to_csv(a.saida / "legis_detalhe_munzona.csv", index=False)
    print("unidades (seções):", len(pres))


if __name__ == "__main__":
    main()
