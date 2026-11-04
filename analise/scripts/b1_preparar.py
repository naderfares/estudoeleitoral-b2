"""Adendo 1, análise B1 (polos estreitos): monta uma raiz de análise alternativa sem mexer no código congelado.

Na análise principal, os polos são as coligações formais do 1º turno. Em B1, cada polo é só a agremiação do
próprio finalista: Federação PT/PCdoB/PV de um lado e PL do outro. Em vez de alterar os scripts congelados
(ei.py, cf.py, behaviors.py, motor_v4.py, rodar_preregistro.py e os das variantes contextual e ordinal), este
script cria uma raiz nova em que as demais agremiações da coligação de Lula recebem um rótulo novo. Como o
mapa de blocos do código congelado não reconhece esses rótulos, elas caem no bloco intermediário 2
("centro_demais" no código). A regra de cadeiras não depende do nome da lista, então o resultado real e o
contrafactual zerado continuam iguais aos oficiais.

No Senado vale a mesma ideia, com a mesma regra para os dois lados: o candidato entra no campo de um finalista
se o seu partido é o do finalista (PT, PCdoB ou PV, que formam a federação de Lula; PL do lado de Flávio) ou se
a coligação da candidatura ao Senado inclui o partido do finalista (PT ou PL).

Uso:
  python3 -I scripts/b1_preparar.py ORIGEM DESTINO              # raiz B1 com os dados reais
  python3 -I scripts/b1_preparar.py ORIGEM DESTINO --embaralhar  # raiz para teste de fumaça (votos de deputado
                                                                   # trocados de unidade dentro de cada UF)
ORIGEM é a pasta analise/ da análise principal. DESTINO não pode existir.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROTULO = {"PSOL / REDE": "PSOL / REDE [B1]", "PSB": "PSB [B1]", "PDT": "PDT [B1]"}
L_PROPRIO = {"PT", "PCDOB", "PV"}
F_PROPRIO = {"PL"}
KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA"]


def tokens(s):
    return {t.strip().upper() for t in re.split(r"[/,]", str(s)) if t.strip()}


def campo_senado(r):
    partido = str(r.partido).upper()
    com = tokens(r.composicao_coligacao)
    if partido in L_PROPRIO:
        return "L"
    if partido in F_PROPRIO:
        return "F"
    if "PT" in com:
        return "L"
    if "PL" in com:
        return "F"
    return "N"


def ligar(orig, dest):
    dest.symlink_to(orig.resolve(), target_is_directory=orig.is_dir())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("origem", type=Path)
    ap.add_argument("destino", type=Path)
    ap.add_argument("--embaralhar", action="store_true")
    a = ap.parse_args()
    o, d = a.origem, a.destino
    if d.exists():
        sys.exit(f"{d} já existe")
    d.mkdir(parents=True)
    ligar(o / "scripts", d / "scripts")
    for sub in ("review", "preregistro"):
        (d / sub).mkdir()

    # dados por UF: novos rótulos nas listas da Câmara
    (d / "data").mkdir()
    for f in sorted((o / "data").iterdir()):
        if f.name in ("camara_partidos_2026.csv", "camara_candidatos_2026.csv"):
            df = pd.read_csv(f, keep_default_na=False)
            df["agremiacao"] = df.agremiacao.replace(ROTULO)
            df.to_csv(d / "data" / f.name, index=False)
        else:
            ligar(f, d / "data" / f.name)

    # dados por zona: mesmos rótulos; no teste de fumaça, votos de deputado trocados de unidade dentro da UF
    (d / "munzona").mkdir()
    for f in sorted((o / "munzona").iterdir()):
        if f.name == "dep_munzona.csv":
            df = pd.read_csv(f)
            df["agremiacao"] = df.agremiacao.replace(ROTULO)
            if a.embaralhar:
                # composição do voto de deputado embaralhada dentro de cada unidade (fator aleatório forte por
                # lista), com o total da unidade mantido, para que os totais de comparecimento continuem coerentes
                rng = np.random.default_rng(7)
                tot = df.groupby(KEY).votos.transform("sum")
                v = df.votos * np.exp(rng.normal(0, 1.0, len(df)))
                df["votos"] = (v * tot / v.groupby([df[k] for k in KEY]).transform("sum")).round().astype(int)
            df.to_csv(d / "munzona" / f.name, index=False)
        else:
            ligar(f, d / "munzona" / f.name)

    # resultados da versão 1: só o campo dos candidatos ao Senado muda
    (d / "results").mkdir()
    for f in sorted((o / "results").iterdir()):
        if f.name == "senado_simulacao.csv":
            df = pd.read_csv(f, keep_default_na=False)
            df["campo_restrito_uf"] = df.apply(campo_senado, axis=1)
            df.to_csv(d / "results" / f.name, index=False)
        else:
            ligar(f, d / "results" / f.name)

    (d / "preregistro" / "LEIA-ME.md").write_text(
        "Raiz da análise B1 do adendo 1 (polos estreitos).\n\n"
        "A corrida só roda depois do registro do adendo 1 no OSF. Grave o link do adendo em OSF_REGISTRADO.txt "
        "nesta pasta.\n" + ("\nESTA RAIZ É DE TESTE DE FUMAÇA: os votos de deputado foram trocados de unidade. "
                            "Nenhum número produzido aqui tem significado.\n" if a.embaralhar else ""))
    print(f"raiz B1 criada em {d}" + (" (teste de fumaça)" if a.embaralhar else ""))


if __name__ == "__main__":
    main()
