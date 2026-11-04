"""Teste: a corrida em pedaços (b2_tabela.py + b2_juntar.py) grava exatamente os mesmos arquivos que ei_bayes.py.

Usa cadeias curtas, só para conferir o encadeamento; os números não têm significado e não são lidos.
Uso: python3 -I scripts/teste_b2_pedacos.py [--ufs AC,RR]
"""
import argparse
import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
CURTO = ["--sorteios", "5", "--por-cadeia", "40", "--aquecimento", "40"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ufs", default="AC,RR")
    a = ap.parse_args()
    py, sc = sys.executable, R / "scripts"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        inteiro, pedacos, juntado = tmp / "inteiro", tmp / "pedacos", tmp / "juntado"
        subprocess.run([py, "-I", sc / "ei_bayes.py", R / "munzona", inteiro, R / "results2_n0_20", "--ufs", a.ufs, *CURTO],
                       check=True, capture_output=True)
        for uf in a.ufs.split(","):
            for t in ("fluxo", "deputado_blocos"):
                subprocess.run([py, "-I", sc / "b2_tabela.py", R / "munzona", pedacos, uf, t, *CURTO],
                               check=True, capture_output=True)
        subprocess.run([py, "-I", sc / "b2_juntar.py", R / "munzona", pedacos, juntado, R / "results2_n0_20",
                        "--sorteios", "5", "--ufs", a.ufs], check=True, capture_output=True)
        arquivos = sorted(p.relative_to(inteiro) for p in inteiro.rglob("*") if p.is_file())
        diferentes = [str(p) for p in arquivos if not (juntado / p).exists() or not filecmp.cmp(inteiro / p, juntado / p, shallow=False)]
        extras = [str(p.relative_to(juntado)) for p in juntado.rglob("*") if p.is_file() and not (inteiro / p.relative_to(juntado)).exists()]
        print(f"{len(arquivos)} arquivos comparados; diferentes: {diferentes or 'nenhum'}; a mais: {extras or 'nenhum'}")
        if diferentes or extras:
            sys.exit(1)
    print("ok: os pedaços reproduzem ei_bayes.py byte a byte")


if __name__ == "__main__":
    main()
