"""Planilha v2: método revisado (fluxos entre turnos + perfis legislativos por inferência ecológica)."""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

DATA, ROOT, OUTF = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
R = ROOT / "results2_n0_20"
F = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
BODY = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
TITLE = Font(name=F, size=14, bold=True)
NOTE = Font(name=F, size=9, italic=True, color="555555")
HL = PatternFill("solid", fgColor="FFF2CC")
L_PART = {"PT", "PCDOB", "PV", "PSB", "PDT", "PSOL", "REDE"}
wb = Workbook()


def write_table(ws, df, start_row=1, numfmt=None, widths=None):
    numfmt = numfmt or {}
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(row=start_row, column=j, value=str(col))
        c.font, c.fill = HDR_FONT, HDR_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(df.itertuples(index=False), start_row + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            if isinstance(v, bool) or type(v).__name__ == "bool_":
                v = "sim" if v else "não"
            if hasattr(v, "item"):
                v = v.item()
            c = ws.cell(row=i, column=j, value=v)
            c.font = BODY
            col = df.columns[j - 1]
            if col in numfmt:
                c.number_format = numfmt[col]
            elif isinstance(v, int):
                c.number_format = "#,##0"
    for j, col in enumerate(df.columns, 1):
        w = (widths or {}).get(col)
        if w is None:
            sample = [len(str(col))] + [len(str(x)) for x in df[col].head(300)]
            w = min(max(sample) + 2, 45)
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(df.columns))}{start_row + len(df)}"
    return start_row + len(df)


def hdr(ws, row, col, text, width=None):
    c = ws.cell(row=row, column=col, value=text)
    c.font, c.fill = HDR_FONT, HDR_FILL
    c.alignment = Alignment(wrap_text=True, vertical="center")
    if width:
        ws.column_dimensions[get_column_letter(col)].width = width


# =============== Leia-me ===============
ws = wb.active
ws.title = "Leia-me"
txt = [
    ("Eleições 2026: e se o 2º turno tivesse acontecido no 1º? (versão 2, método revisado)", TITLE),
    ("", BODY),
    ("A pergunta", BOLD),
    ("Como ficariam Câmara e Senado se a virada de Lula entre o 1º e o 2º turno já tivesse acontecido no 1º turno?", BODY),
    ("", BODY),
    ("Por que a versão 1 foi substituída", BOLD),
    ("A versão 1 aplicava o ganho de Lula no voto 'Lula contra Flávio' só à divisão de votos entre PL e partidos da coligação de Lula. Isso ignora que metade dos eleitores de Lula e de Flávio vota em outros partidos para deputado e senador (MDB, PSD, PP, União etc.), e trata como se a virada tivesse vindo de eleitores trocando de lado, o que os dados mostram que quase não aconteceu.", BODY),
    ("", BODY),
    ("Método da versão 2", BOLD),
    ("1. De onde vieram os votos do 2º turno. Com dados das ~6 mil combinações município/zona do TSE, estimei por UF o fluxo de eleitores entre categorias do 1º turno (Lula, Flávio, outros presidenciáveis, branco/nulo, abstenção) e do 2º (Lula, Flávio, branco/nulo, abstenção). Técnica: inferência ecológica (regressão de Goodman com restrições), calibrada para bater exatamente com os totais reais de cada UF. Aba Fluxo 1T-2T.", BODY),
    ("2. Em quem cada eleitor vota para o Legislativo. Pelo mesmo método, estimei por UF como os eleitores de Lula, de Flávio e dos demais distribuíram o voto para deputado (por bloco: PL, coligação de Lula, centro-direita = Novo/Missão/PP-União/Republicanos, centro e demais, branco/nulo) e para senador (por candidato). Perfis calibrados para reproduzir exatamente os votos reais. Aba Perfis deputado.", BODY),
    ("3. Contrafactual. Só mudam os votos legislativos de quem tem razão lógica para mudar:", BODY),
    ("   - quem se absteve no 1º turno e votou no 2º passa a votar também para deputado e senador, com o perfil dos eleitores do candidato que escolheu, na sua UF;", BODY),
    ("   - quem trocou Flávio por Lula (ou o contrário) troca o perfil legislativo de um pelo do outro (são poucos: ~110 mil);", BODY),
    ("   - todo mundo que votou no 1º turno mantém o voto legislativo que deu de fato, inclusive quem votou nos outros presidenciáveis, quem votou branco/nulo e quem faltou no 2º turno.", BODY),
    ("4. Câmara: o ganho/perda de cada bloco é dividido entre seus partidos pela votação real; cadeiras recalculadas com as regras de 2026 (quociente, 10%/80%/20%, 3ª fase das sobras). O cálculo reproduz exatamente as vagas reais nas 27 UFs. Senado: dois mais votados por UF.", BODY),
    ("", BODY),
    ("Cenários", BOLD),
    ("A (principal): regras do item 3.", BODY),
    ("B (teto): A + os eleitores dos outros presidenciáveis que escolheram Lula ou Flávio no 2º turno passam a votar no Legislativo como os eleitores dessa escolha. Como não dá para estimar com confiança em quem eles votaram de fato (poucos e espalhados: a estimativa oscila de 0% a 100% conforme a UF), assume-se que votavam como a média da UF.", BODY),
    ("A_liq (sensibilidade): A + quem votou no 1º e faltou no 2º perde o voto legislativo. Descartado como principal: faltar no 2º turno tem mais a ver com não haver disputa estadual do que com a eleição presidencial (exemplo: no PA, isso tiraria votos de Chicão e daria a vaga ao PL).", BODY),
    ("Âncora estatística (N0): em UFs com poucas zonas (RR 16, AP 18, DF 19, AC 23), as estimativas são puxadas para a média (nacional nos fluxos, da UF nos perfis), com peso de N0 = 20 unidades. A aba Sensibilidade mostra N0 = 0, 20 e 100: as conclusões não mudam.", BODY),
    ("", BODY),
    ("Limitações", BOLD),
    ("Inferência ecológica estima comportamentos médios a partir de resultados agregados, não de eleitores individuais; o ajuste do voto para deputado é fraco (voto muito local), por isso uso blocos. O branco/nulo do 1º turno foi em boa parte para Lula no 2º; como parte disso é erro na urna de 6 cargos, esses eleitores mantêm o voto legislativo real.", BODY),
    ("Fonte: TSE, API de resultados (resultados.tse.jus.br/oficial/ele2026) e dados abertos por município/zona (cdn.tse.jus.br/estatistica/sead/odsele), baixados em 01/11/2026. Cadeiras e votos simulados são calculados em Python; diferenças e totais nesta planilha são fórmulas.", NOTE),
]
for i, (t, f) in enumerate(txt, 1):
    c = ws.cell(row=i, column=1, value=t)
    c.font = f
    c.alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width = 140

# =============== Resultado Câmara ===============
tab = pd.read_csv(R / "camara_cf_bancadas.csv", index_col=0)[["real", "A", "B", "modelo_antigo_restrito"]].reset_index()
tab.columns = ["partido", "real", "A (principal)", "B (teto)", "versão 1 (descartada)"]
tab["campo"] = tab.partido.map(lambda p: "coligação Lula" if p in L_PART else ("PL" if p == "PL" else "outros"))
ws = wb.create_sheet("Resultado Câmara")
write_table(ws, tab)
n = len(tab)
for col, h, src in ((7, "dif A", "C"), (8, "dif B", "D"), (9, "dif versão 1", "E")):
    hdr(ws, 1, col, h, 12)
    for r in range(2, n + 2):
        c = ws.cell(row=r, column=col, value=f"={src}{r}-$B{r}")
        c.font, c.number_format = BODY, "+0;-0;0"
tr = n + 2
ws.cell(row=tr, column=1, value="TOTAL").font = BOLD
for col in [2, 3, 4, 5, 7, 8, 9]:
    L = get_column_letter(col)
    ws.cell(row=tr, column=col, value=f"=SUM({L}2:{L}{n + 1})").font = BOLD
r0 = tr + 2
ws.cell(row=r0, column=1, value="Blocos").font = BOLD
for k, crit in enumerate(("coligação Lula", "PL", "outros")):
    rr = r0 + 1 + k
    ws.cell(row=rr, column=1, value=crit).font = BODY
    for col in [2, 3, 4, 5, 7, 8, 9]:
        L = get_column_letter(col)
        c = ws.cell(row=rr, column=col, value=f'=SUMIF($F$2:$F${n + 1},"{crit}",{L}2:{L}{n + 1})')
        c.font = BODY
        if col >= 7:
            c.number_format = "+0;-0;0"
ws.cell(row=r0 + 5, column=1, value="Maioria simples: 257 | PEC: 308. Coligação Lula = PT, PCdoB, PV, PSB, PDT, PSOL, Rede (coligação presidencial do 1º turno).").font = NOTE
ws.auto_filter.ref = None

# =============== Câmara mudanças por UF ===============
cam = pd.read_csv(R / "camara_cf_agremiacoes.csv")
mud = cam[(cam.cenario.isin(["A", "B"])) & (cam.vagas_sim != cam.vagas_real)]
mud = mud[["cenario", "uf", "agremiacao", "bloco", "votos_real", "votos_sim", "vagas_real", "vagas_sim"]].sort_values(["cenario", "uf"])
ws = wb.create_sheet("Câmara mudanças UF")
end = write_table(ws, mud)
hdr(ws, 1, 9, "dif vagas", 10)
for r in range(2, end + 1):
    c = ws.cell(row=r, column=9, value=f"=H{r}-G{r}")
    c.font, c.number_format = BODY, "+0;-0;0"

# =============== Senado ===============
s = pd.read_csv(R / "senado_cf.csv")
rows = []
for uf, g in s.groupby("uf"):
    rec = dict(UF=uf)
    for lab, col in (("real", "votos"), ("A", "votos_A"), ("B", "votos_B")):
        g2 = g.sort_values(col, ascending=False)
        rec[f"eleitos {lab}"] = f"{g2.iloc[0].candidato} ({g2.iloc[0].partido}) / {g2.iloc[1].candidato} ({g2.iloc[1].partido})"
        rec[f"3º lugar {lab}"] = f"{g2.iloc[2].candidato} ({g2.iloc[2].partido})"
        rec[f"margem 2º-3º {lab}"] = int(round(g2.iloc[1][col] - g2.iloc[2][col]))
    rec["muda em A?"] = rec["eleitos A"] != rec["eleitos real"] and set(rec["eleitos A"].split(" / ")) != set(rec["eleitos real"].split(" / "))
    rec["muda em B?"] = set(rec["eleitos B"].split(" / ")) != set(rec["eleitos real"].split(" / "))
    rows.append(rec)
sm = pd.DataFrame(rows).sort_values("margem 2º-3º A")
sm = sm[["UF", "eleitos real", "3º lugar real", "margem 2º-3º real", "eleitos A", "3º lugar A", "margem 2º-3º A",
         "muda em A?", "eleitos B", "margem 2º-3º B", "muda em B?"]]
ws = wb.create_sheet("Resultado Senado")
ws.cell(row=1, column=1, value="Margem entre o 2º eleito e o 3º colocado em cada cenário (ordenado pela margem no cenário A). Margem pequena = vaga em disputa.").font = NOTE
end = write_table(ws, sm, start_row=2, widths={"eleitos real": 48, "eleitos A": 48, "eleitos B": 48, "3º lugar real": 32, "3º lugar A": 32})
for r in range(3, end + 1):
    if ws.cell(row=r, column=8).value == "sim" or ws.cell(row=r, column=11).value == "sim":
        for col in range(1, 12):
            ws.cell(row=r, column=col).fill = HL
sd = s[["uf", "numero", "candidato", "partido", "composicao_coligacao", "votos", "votos_A", "votos_B", "eleito", "eleito_A", "eleito_B"]].copy()
for c_ in ("votos_A", "votos_B"):
    sd[c_] = sd[c_].round().astype(int)
sd["eleito"] = sd.eleito.astype(str).map({"True": "sim", "False": ""})
for c_ in ("eleito_A", "eleito_B"):
    sd[c_] = sd[c_].astype(str).map({"True": "sim", "False": ""})
ws = wb.create_sheet("Senado candidatos")
write_table(ws, sd.sort_values(["uf", "votos"], ascending=[True, False]), widths={"composicao_coligacao": 45})

# =============== Fluxo ===============
fl = pd.read_csv(R / "fluxos_por_uf.csv")
ORD_O = ["lula1", "flavio1", "outros1", "bn1", "abst1"]
ORD_D = ["lula2", "flavio2", "bn2", "abst2"]
NOMES_O = {"lula1": "Lula (1T)", "flavio1": "Flávio (1T)", "outros1": "Outros presidenciáveis (1T)", "bn1": "Branco/nulo (1T)", "abst1": "Abstenção (1T)"}
NOMES_D = {"lula2": "Lula (2T)", "flavio2": "Flávio (2T)", "bn2": "Branco/nulo (2T)", "abst2": "Abstenção (2T)"}
br = fl.pivot_table(index="origem", columns="destino", values="votos", aggfunc="sum").loc[ORD_O, ORD_D].round().astype(int)
ws = wb.create_sheet("Fluxo 1T-2T")
ws.cell(row=1, column=1, value="Fluxo estimado de eleitores do 1º para o 2º turno, Brasil (soma das UFs; sem exterior e voto em trânsito)").font = BOLD
hdr(ws, 2, 1, "origem \\ destino", 30)
for j, d in enumerate(ORD_D, 2):
    hdr(ws, 2, j, NOMES_D[d], 16)
hdr(ws, 2, 6, "total 1T", 16)
for i, o in enumerate(ORD_O, 3):
    ws.cell(row=i, column=1, value=NOMES_O[o]).font = BODY
    for j, d in enumerate(ORD_D, 2):
        c = ws.cell(row=i, column=j, value=int(br.loc[o, d]))
        c.font, c.number_format = BODY, "#,##0"
    c = ws.cell(row=i, column=6, value=f"=SUM(B{i}:E{i})")
    c.font, c.number_format = BOLD, "#,##0"
ws.cell(row=8, column=1, value="total 2T").font = BOLD
for j in range(2, 7):
    L = get_column_letter(j)
    c = ws.cell(row=8, column=j, value=f"=SUM({L}3:{L}7)")
    c.font, c.number_format = BOLD, "#,##0"
ws.cell(row=10, column=1, value="Em % da origem").font = BOLD
for j, d in enumerate(ORD_D, 2):
    hdr(ws, 11, j, NOMES_D[d])
for i, o in enumerate(ORD_O, 12):
    ws.cell(row=i, column=1, value=NOMES_O[o]).font = BODY
    for j in range(2, 6):
        L = get_column_letter(j)
        c = ws.cell(row=i, column=j, value=f"={L}{i - 9}/$F{i - 9}")
        c.font, c.number_format = BODY, "0.0%"
ws.cell(row=18, column=1, value="Fluxo por UF").font = BOLD
flu = fl.assign(origem=fl.origem.map(NOMES_O), destino=fl.destino.map(NOMES_D))[["uf", "origem", "destino", "votos"]]
flu["votos"] = flu.votos.round().astype(int)
write_table(ws, flu, start_row=19)
ws.freeze_panes = None

# =============== Perfis ===============
pc = pd.read_csv(R / "perfis_calibrados.csv", index_col=0)
cols = ["PL", "coligacao_lula", "centro_direita", "centro_demais", "_branco_nulo"]
pdp = pc[pc.cargo == "deputado"].reset_index().rename(columns={"index": "origem"})[["uf", "origem"] + cols]
w = fl.groupby(["uf", "origem"]).votos.sum()
ws = wb.create_sheet("Perfis deputado")
ws.cell(row=1, column=1, value="Voto para deputado federal dos eleitores de cada categoria do 1º turno presidencial (Brasil, média ponderada das UFs)").font = BOLD
nat = {}
for o in ["lula1", "flavio1", "outros1", "bn1"]:
    sub = pdp[pdp.origem == o].set_index("uf")[cols]
    ww = w.xs(o, level="origem").reindex(sub.index)
    nat[o] = sub.mul(ww, axis=0).sum() / ww.sum()
nat = pd.DataFrame(nat)
NB = {"PL": "PL", "coligacao_lula": "Coligação Lula (PT, PCdoB, PV, PSB, PDT, PSOL, Rede)", "centro_direita": "Centro-direita (Novo, Missão, PP/União, Republicanos)",
      "centro_demais": "Centro e demais (MDB, PSD, Podemos, PSDB/Cidadania etc.)", "_branco_nulo": "Branco/nulo"}
hdr(ws, 2, 1, "bloco", 55)
for j, o in enumerate(["lula1", "flavio1", "outros1", "bn1"], 2):
    hdr(ws, 2, j, NOMES_O[o], 18)
for i, b in enumerate(cols, 3):
    ws.cell(row=i, column=1, value=NB[b]).font = BODY
    for j, o in enumerate(["lula1", "flavio1", "outros1", "bn1"], 2):
        c = ws.cell(row=i, column=j, value=float(nat.loc[b, o]))
        c.font, c.number_format = BODY, "0.0%"
ws.cell(row=8, column=1, value="total").font = BOLD
for j in range(2, 6):
    L = get_column_letter(j)
    c = ws.cell(row=8, column=j, value=f"=SUM({L}3:{L}7)")
    c.font, c.number_format = BOLD, "0.0%"
ws.cell(row=9, column=1, value="Atenção: o perfil dos 'outros presidenciáveis' e do branco/nulo é pouco confiável (categorias pequenas); não é usado no cenário A.").font = NOTE
ws.cell(row=11, column=1, value="Perfis por UF (proporção dos eleitores da categoria)").font = BOLD
pdp2 = pdp.assign(origem=pdp.origem.map(NOMES_O))
write_table(ws, pdp2, start_row=12, numfmt={c: "0.0%" for c in cols})
ws.freeze_panes = None

# =============== Sensibilidade ===============
rows = []
for n0 in (0, 20, 100):
    tb = pd.read_csv(ROOT / f"results2_n0_{n0}" / "camara_cf_bancadas.csv", index_col=0)
    ss = pd.read_csv(ROOT / f"results2_n0_{n0}" / "senado_cf.csv")
    for cen in ("A", "B", "A_liq"):
        flips = []
        for uf, g in ss.groupby("uf"):
            sai = g[(g.eleito.astype(str) == "True") & ~g[f"eleito_{cen}"]]
            ent = g[(g.eleito.astype(str) != "True") & g[f"eleito_{cen}"]]
            for (_, a), (_, b) in zip(sai.iterrows(), ent.iterrows()):
                flips.append(f"{uf}: {a.candidato} ({a.partido}) -> {b.candidato} ({b.partido})")
        rows.append({"N0 (âncora)": n0, "cenário": cen, "PL": int(tb.loc["PL", cen]), "PT": int(tb.loc["PT", cen]),
                     "coligação Lula": int(tb.loc[tb.index.isin(L_PART), cen].sum()),
                     "Senado: vagas que mudam": "; ".join(flips) if flips else "nenhuma"})
sens = pd.DataFrame(rows)
ws = wb.create_sheet("Sensibilidade")
ws.cell(row=1, column=1, value="Real: PL 121, PT 70, coligação Lula 124. Principal: N0 = 20, cenário A.").font = NOTE
end = write_table(ws, sens, start_row=2, widths={"Senado: vagas que mudam": 110})
for r in range(3, end + 1):
    if ws.cell(row=r, column=1).value == 20 and ws.cell(row=r, column=2).value == "A":
        for col in range(1, 7):
            ws.cell(row=r, column=col).fill = HL

# =============== Verificações ===============
chk = [
    ("Totais nacionais de presidente (1º e 2º turno) iguais aos do TSE", "OK"),
    ("54 senadores e 513 deputados eleitos reproduzidos a partir dos dados", "OK"),
    ("Cálculo de cadeiras da Câmara reproduz as vagas reais nas 27 UFs", "OK (0 divergências)"),
    ("Dados por município/zona somam exatamente os totais da API (deputado e senado)", "OK (diferença 0 voto)"),
    ("Fluxos: linhas = totais do 1º turno por UF", "OK (erro 0 voto)"),
    ("Fluxos: colunas = totais do 2º turno por UF", "OK (erro máx. 293 votos, por diferença de aptos entre turnos)"),
    ("Perfis calibrados reproduzem os votos reais por bloco em cada UF", "OK (erro relativo ~1e-16)"),
    ("Votos válidos adicionados para deputado <= eleitores novos (A: 3,38 mi; B: 3,65 mi; novos: 4,11 mi)", "OK"),
    ("513 cadeiras e 54 senadores em todos os cenários; nenhum voto negativo", "OK"),
    ("Conclusões estáveis com âncora N0 = 0, 20 e 100 (aba Sensibilidade)", "OK"),
]
ws = wb.create_sheet("Verificações")
write_table(ws, pd.DataFrame(chk, columns=["verificação", "resultado"]), widths={"verificação": 95, "resultado": 55})

# =============== Câmara detalhado e swing ===============
ws = wb.create_sheet("Câmara agremiações")
write_table(ws, cam[["cenario", "uf", "agremiacao", "bloco", "votos_real", "votos_sim", "vagas_real", "vagas_sim", "qe_sim"]].sort_values(["cenario", "uf", "votos_real"], ascending=[True, True, False]))

sw = pd.read_csv(ROOT / "results" / "swing_por_uf.csv")[["uf", "lula_1t", "flavio_1t", "lula_2t", "flavio_2t"]]
ws = wb.create_sheet("Presidente por UF")
end = write_table(ws, sw)
for col, h in ((6, "Lula % bipartidário 1T"), (7, "Lula % bipartidário 2T"), (8, "variação (p.p.)")):
    hdr(ws, 1, col, h, 16)
for r in range(2, end + 1):
    ws.cell(row=r, column=6, value=f"=B{r}/(B{r}+C{r})").number_format = "0.00%"
    ws.cell(row=r, column=7, value=f"=D{r}/(D{r}+E{r})").number_format = "0.00%"
    ws.cell(row=r, column=8, value=f"=(G{r}-F{r})*100").number_format = "+0.00;-0.00"
    for col in (6, 7, 8):
        ws.cell(row=r, column=col).font = BODY

# =============== Dados brutos ===============
for nome, arq in (("Dados presidente", "presidente_por_uf_1t_2t.csv"), ("Dados senado", "senado_candidatos_2026.csv"),
                  ("Dados câmara partidos", "camara_partidos_2026.csv"), ("Dados câmara candidatos", "camara_candidatos_2026.csv")):
    df = pd.read_csv(DATA / arq, keep_default_na=False)
    ws = wb.create_sheet(nome)
    write_table(ws, df)

wb.save(OUTF)
print("ok", OUTF)
