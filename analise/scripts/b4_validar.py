"""Adendo, análise B4: compara fluxos e perfis da inferência ecológica com dados individuais (ESEB).

Os nomes e códigos das variáveis do ESEB 2026 ainda não são conhecidos, então ficam num arquivo JSON de
mapeamento, preenchido quando a base sair, antes de rodar. Exemplo de mapeamento:

{
  "peso": "PESO",
  "voto_1t": {"variavel": "Q10", "codigos": {"lula1": [1], "flavio1": [2], "outros1": [3, 4, 5], "bn1": [96, 97], "abst1": [99]}},
  "voto_2t": {"variavel": "Q12", "codigos": {"lula2": [1], "flavio2": [2], "bn2": [96, 97], "abst2": [99]}},
  "deputado": {"variavel": "Q15", "codigos": {"PL": [22], "coligacao_lula": [13, 65, 43, 50, 18, 40, 12],
               "centro_direita": [30, 28, 11, 44, 10], "_branco_nulo": [96, 97]}, "resto": "centro_demais"}
}

Respostas fora dos códigos (não sabe, não respondeu) saem da tabela daquela pergunta. No deputado, códigos de
partido não listados vão para "resto". O voto lembrado tende a superestimar o voto no vencedor; o script não
corrige isso.

Regras de alerta fixadas no adendo: diferença acima de 10 pontos percentuais em qualquer perfil nacional, ou
fluxo que a inferência põe no limite zero (taxa nacional abaixo de 0,1%) e que o ESEB estima acima de 2% da origem.

Uso: python3 -I scripts/b4_validar.py MICRODADOS.csv MAPEAMENTO.json RESULTADOS_EI SAIDA
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ORIG_T = ["lula1", "flavio1", "outros1", "bn1", "abst1"]
DEST_T = ["lula2", "flavio2", "bn2", "abst2"]
ORIG_L = ["lula1", "flavio1", "outros1", "bn1"]
BLOCOS = ["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]
LIM_PERFIL, LIM_ZERO_EI, LIM_FLUXO = 0.10, 0.001, 0.02


def recodifica(s, cod, resto=None):
    inv = {v: k for k, vs in cod.items() for v in vs}
    out = s.map(inv)
    if resto is not None:
        out = out.where(out.notna() | s.isna(), resto)
    return out


def tabela(df, lin, col, w, linhas, colunas):
    t = df.dropna(subset=[lin, col]).pivot_table(index=lin, columns=col, values=w, aggfunc="sum", fill_value=0)
    t = t.reindex(index=linhas, columns=colunas, fill_value=0)
    return t.div(t.sum(1).replace(0, np.nan), axis=0)


def compara(micro, mapa, ei):
    df = micro.copy()
    w = mapa.get("peso")
    if not w:
        df["_w"], w = 1.0, "_w"
    df["o"] = recodifica(df[mapa["voto_1t"]["variavel"]], mapa["voto_1t"]["codigos"])
    df["d"] = recodifica(df[mapa["voto_2t"]["variavel"]], mapa["voto_2t"]["codigos"])
    dep = mapa["deputado"]
    df["b"] = recodifica(df[dep["variavel"]], dep["codigos"], dep.get("resto"))
    fl_s = tabela(df, "o", "d", w, ORIG_T, DEST_T)
    pf_s = tabela(df, "o", "b", w, ORIG_L, BLOCOS)

    fl = pd.read_csv(ei / "fluxos_por_uf.csv").groupby(["origem", "destino"]).votos.sum().unstack()
    fl_e = fl.reindex(index=ORIG_T, columns=DEST_T)
    fl_e = fl_e.div(fl_e.sum(1), axis=0)
    pc = pd.read_csv(ei / "perfis_calibrados.csv", index_col=0)
    pc = pc[pc.cargo == "deputado"]
    # perfil nacional da inferência: média dos perfis das UFs ponderada pelo tamanho de cada grupo na UF
    fl_uf = pd.read_csv(ei / "fluxos_por_uf.csv").groupby(["uf", "origem"]).votos.sum()
    linhas = []
    for o in ORIG_L:
        sub = pc.loc[[o]] if o in pc.index else pc.iloc[0:0]
        pesos = np.array([fl_uf.get((u, o), 0.0) for u in sub.uf])
        linhas.append((sub[BLOCOS].values * pesos[:, None]).sum(0) / pesos.sum())
    pf_e = pd.DataFrame(linhas, index=ORIG_L, columns=BLOCOS)

    alertas = []
    dif = (pf_s - pf_e)
    for o in ORIG_L:
        for b in BLOCOS:
            if abs(dif.loc[o, b]) > LIM_PERFIL:
                alertas.append(f"perfil {o} -> {b}: ESEB {pf_s.loc[o, b]:.3f}, inferência {pf_e.loc[o, b]:.3f}")
    for o in ORIG_T:
        for d in DEST_T:
            if fl_e.loc[o, d] < LIM_ZERO_EI and fl_s.loc[o, d] > LIM_FLUXO:
                alertas.append(f"fluxo {o} -> {d}: no limite zero na inferência, {fl_s.loc[o, d]:.3f} no ESEB")
    h2 = {}
    for o, nome in (("lula1", "lula"), ("flavio1", "flavio")):
        for fonte, t in (("eseb", pf_s), ("inferencia", pf_e)):
            v = t.loc[o]
            h2[f"h2_{nome}_{fonte}"] = float((v["centro_direita"] + v["centro_demais"]) / (1 - v["_branco_nulo"]))
    return fl_s, fl_e, pf_s, pf_e, alertas, h2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("micro", type=Path)
    ap.add_argument("mapa", type=Path)
    ap.add_argument("ei", type=Path)
    ap.add_argument("saida", type=Path)
    a = ap.parse_args()
    micro = pd.read_csv(a.micro, sep=None, engine="python")
    mapa = json.loads(a.mapa.read_text())
    fl_s, fl_e, pf_s, pf_e, alertas, h2 = compara(micro, mapa, a.ei)
    a.saida.mkdir(parents=True, exist_ok=True)
    fl_s.to_csv(a.saida / "fluxos_eseb.csv")
    fl_e.to_csv(a.saida / "fluxos_inferencia.csv")
    pf_s.to_csv(a.saida / "perfis_eseb.csv")
    pf_e.to_csv(a.saida / "perfis_inferencia.csv")
    (a.saida / "alertas.txt").write_text("\n".join(alertas) or "nenhum alerta")
    (a.saida / "h2.json").write_text(json.dumps(h2, indent=1))
    print(f"{len(alertas)} alerta(s); saída em {a.saida}")


if __name__ == "__main__":
    main()
