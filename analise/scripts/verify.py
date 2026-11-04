"""Segunda verificação: consistência contábil de fluxos, perfis e contrafactual."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
R2, MZ = Path(sys.argv[1]), Path(sys.argv[2])
ORIG = ["lula1", "flavio1", "outros1", "bn1"]
ok = True


def check(nome, cond, info=""):
    global ok
    ok &= bool(cond)
    print(f"[{'OK ' if cond else 'ERRO'}] {nome} {info}")


fl = pd.read_csv(R2 / "fluxos_por_uf.csv")
pres = pd.read_csv(MZ / "pres_munzona.csv")
dep = pd.read_csv(MZ / "dep_munzona.csv")
ldet = pd.read_csv(MZ / "legis_detalhe_munzona.csv")
pc = pd.read_csv(R2 / "perfis_calibrados.csv", index_col=0)
cam = pd.read_csv(R2 / "camara_cf_agremiacoes.csv")
sen = pd.read_csv(R2 / "senado_cf.csv")

# 1. fluxos fecham com os totais dos dois turnos
tot1 = pres.groupby("SG_UF")[["lula1", "flavio1", "outros1", "bn1", "abst1"]].sum().stack()
tot2 = pres.groupby("SG_UF")[["lula2", "flavio2", "bn2", "abst2"]].sum().stack()
r = fl.groupby(["uf", "origem"]).votos.sum()
c = fl.groupby(["uf", "destino"]).votos.sum()
er1 = (r - tot1.reindex(r.index)).abs().max()
er2 = (c - tot2.reindex(c.index)).abs().max() if True else 0
check("fluxos: linhas = totais do 1º turno por UF", er1 < 2, f"(maior erro {er1:.2f} votos)")
check("fluxos: colunas = totais do 2º turno por UF", er2 / tot2.sum() < 1e-5, f"(maior erro {er2:.0f} votos, efeito da pequena diferença de aptos entre turnos)")
check("fluxos: nenhuma taxa negativa", (fl.votos >= -1e-6).all())

# 2. perfis calibrados reproduzem votos reais
erros = []
for uf in pres.SG_UF.unique():
    n1 = pres[pres.SG_UF == uf][ORIG].sum().values.astype(float)
    P = pc[(pc.uf == uf) & (pc.cargo == "deputado")][["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]]
    imp = (P.values * n1[:, None]).sum(0)
    BL = {"PL": "PL", "PCDOB / PT / PV": "coligacao_lula", "PSOL / REDE": "coligacao_lula", "PSB": "coligacao_lula", "PDT": "coligacao_lula",
          "NOVO": "centro_direita", "MISSÃO": "centro_direita", "PP / UNIÃO": "centro_direita", "REPUBLICANOS": "centro_direita"}
    d = dep[dep.SG_UF == uf].assign(b=lambda x: x.agremiacao.map(BL).fillna("centro_demais")).groupby("b").votos.sum()
    real = np.array([d.get("PL", 0), d.get("coligacao_lula", 0), d.get("centro_direita", 0), d.get("centro_demais", 0),
                     ldet[(ldet.SG_UF == uf) & (ldet.CD_CARGO == 6)].bn.sum()], dtype=float)
    real = real * n1.sum() / real.sum()  # comparecimento presidencial x legislativo (diferença mínima)
    erros.append(np.abs(imp - real).max() / real.sum())
check("perfis de deputado reproduzem votos reais por bloco", max(erros) < 1e-4, f"(maior erro relativo {max(erros):.2e})")
check("perfis de deputado somam 1 por eleitor", np.allclose(pc[pc.cargo == "deputado"][["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]].sum(axis=1), 1, atol=1e-6))

# 3. contabilidade do contrafactual: votos válidos adicionados x novos eleitores
for cen in ("A", "B"):
    add = cam[cam.cenario == cen].votos_sim.sum() - cam[cam.cenario == cen].votos_real.sum()
    novos = fl[(fl.origem == "abst1") & (fl.destino != "abst2")].votos.sum()
    print(f"      cenário {cen}: votos válidos para deputado adicionados = {add/1e6:.2f} mi | eleitores novos (abstenção 1T -> votou 2T) = {novos/1e6:.2f} mi")
    check(f"cenário {cen}: votos válidos adicionados <= eleitores novos", add <= novos * 1.001)
for cen in ("A", "A_liq", "B"):
    v = cam[cam.cenario == cen]
    check(f"Câmara {cen}: 513 cadeiras", v.vagas_sim.sum() == 513, f"({v.vagas_sim.sum()})")
check("Senado: 54 eleitos em cada cenário", all(sen[f"eleito_{c}"].sum() == 54 for c in ("A", "A_liq", "B")))
check("nenhum voto negativo", (cam.votos_sim >= 0).all() and (sen[["votos_A", "votos_B"]] >= 0).all().all())

# 4. resumo dos fluxos e perfis nacionais
br = fl.pivot_table(index="origem", columns="destino", values="votos", aggfunc="sum").loc[
    ["lula1", "flavio1", "outros1", "bn1", "abst1"], ["lula2", "flavio2", "bn2", "abst2"]]
print("\nFluxo nacional (milhões):"); print((br / 1e6).round(2).to_string())
w = fl.groupby(["uf", "origem"]).votos.sum()
pdp = pc[pc.cargo == "deputado"].reset_index().rename(columns={"index": "origem"})
cols = ["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]
agg = {}
for o in ORIG:
    sub = pdp[pdp.origem == o].set_index("uf")[cols]
    ww = w.xs(o, level="origem").reindex(sub.index)
    agg[o] = (sub.mul(ww, axis=0).sum() / ww.sum() * 100).round(1)
print("\nPerfil nacional do voto para deputado (% dos eleitores de cada categoria):"); print(pd.DataFrame(agg).to_string())
print("\nTUDO OK" if ok else "\nHÁ ERROS")
