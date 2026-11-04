"""Adendo 1, análise B1 (polos estreitos): roda a análise registrada inteira numa raiz criada por b1_preparar.py.

Usa o código congelado sem alteração. Os únicos ajustes são de caminho: os scripts das variantes contextual
(review/ext_goodman.py) e ordinal (review/ordinal.py) têm a pasta da análise escrita no próprio código, então
este script os executa com essa pasta trocada pela raiz B1 e para antes do trecho final deles, que só imprime
cadeiras. A saída deles vai para um log, não para a tela.

Uso:
  python3 -I scripts/b1_rodar.py RAIZ_B1            # corrida real: exige o link do adendo em RAIZ_B1/preregistro/OSF_REGISTRADO.txt
  python3 -I scripts/b1_rodar.py RAIZ_B1 --fumaca   # teste de fumaça numa raiz criada com --embaralhar
"""
import argparse
import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path

CONGELADO = "/Users/nader/workspace/personal/estudoeleitoral/analise"
CORTE = "subprocess.run(['python3', str(R / 'scripts/cf.py')"
PASTA = {"ext_goodman.py": "results2_n0_ext", "ordinal.py": "results2_n0_ord"}


def variante(raiz, script, log):
    """Roda o script da variante até gravar os perfis; o contrafactual (cf.py) roda depois, aqui."""
    fonte = (raiz / "scripts").resolve().parent.joinpath("review", script).read_text()
    assert CONGELADO in fonte and CORTE in fonte, f"{script}: estrutura inesperada"
    fonte = fonte.replace(CONGELADO, str(raiz)).split(CORTE)[0]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(fonte, script, "exec"), {"__name__": "__variante__"})
    log.write(f"--- {script}\n{buf.getvalue()}\n")
    # Regra fixada antes do registro do adendo: se a variante deixar indefinido o perfil de um grupo numa UF
    # (todas as frações estimadas <= 0), esse grupo usa o perfil do modelo principal nessa UF. O número de
    # casos vai para o log e para o artigo.
    import pandas as pd
    od = raiz / PASTA[script]
    p = pd.read_csv(od / "perfis_deputado_blocos.csv")
    base = pd.read_csv(raiz / "results2_n0_20" / "perfis_deputado_blocos.csv").set_index(["uf", "origem", "bloco"]).p
    ruins = p[p.p.isna()][["uf", "origem"]].drop_duplicates()
    for r in ruins.itertuples():
        m = (p.uf == r.uf) & (p.origem == r.origem)
        p.loc[m, "p"] = [base[(r.uf, r.origem, b)] for b in p.loc[m, "bloco"]]
    p.to_csv(od / "perfis_deputado_blocos.csv", index=False)
    log.write(f"{script}: {len(ruins)} perfis indefinidos substituídos pelo modelo principal "
              f"({', '.join(f'{r.uf}/{r.origem}' for r in ruins.itertuples()) or 'nenhum'})\n")
    print(f"{script}: {len(ruins)} perfis indefinidos substituídos pelo modelo principal")
    subprocess.run([sys.executable, str(raiz / "scripts" / "cf.py"), str(od), str(raiz / "data"), str(raiz / "munzona"),
                    str(raiz / "results")], check=True, stdout=log, stderr=log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raiz", type=Path)
    ap.add_argument("--fumaca", action="store_true")
    a = ap.parse_args()
    raiz = a.raiz.resolve()
    lock = raiz / "preregistro" / "OSF_REGISTRADO.txt"
    leia = (raiz / "preregistro" / "LEIA-ME.md").read_text()
    if a.fumaca and "TESTE DE FUMAÇA" not in leia:
        sys.exit("--fumaca só roda numa raiz criada com --embaralhar")
    if not a.fumaca and ("TESTE DE FUMAÇA" in leia or not lock.exists() or "osf.io" not in lock.read_text()):
        sys.exit("Trava ativa: registre o adendo 1 no OSF e grave o link em preregistro/OSF_REGISTRADO.txt da raiz B1.")

    py, sc = sys.executable, raiz / "scripts"
    env = {**os.environ, "ESTUDO_ROOT": str(raiz)}
    log = open(raiz / "log_b1.txt", "w")

    # 1. inferência e contrafactual para as âncoras do plano registrado
    for n0 in (0, 20, 100):
        eo = raiz / f"results2_n0_{n0}"
        subprocess.run([py, str(sc / "ei.py"), str(raiz / "munzona"), str(eo), str(n0)], check=True, stdout=log, stderr=log)
        subprocess.run([py, str(sc / "cf.py"), str(eo), str(raiz / "data"), str(raiz / "munzona"), str(raiz / "results")],
                       check=True, stdout=log, stderr=log)

    # 2. variantes contextual e ordinal
    for s in ("ext_goodman.py", "ordinal.py"):
        variante(raiz, s, log)

    # 3. testes contábeis do motor na raiz B1
    r = subprocess.run([py, str(sc / "testes_v4.py")], env=env, capture_output=True, text=True)
    log.write("--- testes_v4.py\n" + r.stdout + r.stderr)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("testes contábeis falharam; nada mais roda")

    # 4. análise registrada
    if a.fumaca:
        # no teste de fumaça o script registrado não gera reamostragens; geramos duas aqui
        sys.path.insert(0, str(sc))
        os.environ["ESTUDO_ROOT"] = str(raiz)
        import rodar_preregistro as rp  # noqa: E402
        for b in (0, 1):
            rp.gera_boot(b)
        cmd = [py, str(sc / "rodar_preregistro.py"), "--fumaca"]
    else:
        cmd = [py, str(sc / "rodar_preregistro.py")]
    subprocess.run(cmd, env=env, check=True, stdout=log, stderr=log)
    log.close()
    print("pronto; saída em", raiz / ("results4_fumaca" if a.fumaca else "results4"))


if __name__ == "__main__":
    main()
