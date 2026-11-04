"""Monta a planilha final com dados brutos do TSE e resultados da simulação."""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DATA, RES, OUTF = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

F = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
BODY = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
TITLE = Font(name=F, size=14, bold=True)
NOTE = Font(name=F, size=9, italic=True, color="555555")
THIN = Border(bottom=Side(style="thin", color="BFBFBF"))
HL = PatternFill("solid", fgColor="FFF2CC")

wb = Workbook()


def write_table(ws, df, start_row=1, widths=None, numfmt=None, freeze=True):
    numfmt = numfmt or {}
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(row=start_row, column=j, value=col)
        c.font, c.fill = HDR_FONT, HDR_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(df.itertuples(index=False), start_row + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            if isinstance(v, bool) or (type(v).__name__ == "bool_"):
                v = "sim" if v else "não"
            c = ws.cell(row=i, column=j, value=v)
            c.font = BODY
            col = df.columns[j - 1]
            if col in numfmt:
                c.number_format = numfmt[col]
            elif isinstance(v, (int,)) and not isinstance(v, bool):
                c.number_format = "#,##0"
    for j, col in enumerate(df.columns, 1):
        w = (widths or {}).get(col)
        if w is None:
            sample = [len(str(col))] + [len(str(x)) for x in df[col].head(300)]
            w = min(max(sample) + 2, 45)
        ws.column_dimensions[get_column_letter(j)].width = w
    if freeze:
        ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(df.columns))}{start_row + len(df)}"
    return start_row + len(df)


# ---------------- Leia-me ----------------
ws = wb.active
ws.title = "Leia-me"
linhas = [
    ("Eleições 2026: e se a variação do 2º turno valesse no 1º?", TITLE),
    ("", BODY),
    ("O que é", BOLD),
    ("Dados brutos do TSE (1º e 2º turno) e uma simulação de como ficariam Senado e Câmara se a variação de Lula entre os turnos tivesse ocorrido já no 1º turno.", BODY),
    ("", BODY),
    ("Fonte dos dados", BOLD),
    ("API oficial de resultados do TSE: https://resultados.tse.jus.br/oficial/ele2026/ (eleições 6257 = presidente 1º turno, 6258 = presidente 2º turno, 6259 = Senado e deputado federal). Baixado em 01/11/2026.", BODY),
    ("Conferência: totais nacionais de presidente, 54 senadores eleitos e 513 deputados batem com o oficial. O cálculo de cadeiras da Câmara reproduz exatamente as vagas oficiais nas 27 UFs.", BODY),
    ("", BODY),
    ("Método", BOLD),
    ("1. Swing por UF = participação de Lula no voto Lula+Flávio no 2º turno menos a mesma medida no 1º turno (aba Swing por UF).", BODY),
    ("2. Esse swing é aplicado à divisão de votos entre o campo de Lula e o campo de Flávio no Legislativo: transfere-se swing × (votos do campo L + votos do campo F) do campo F para o campo L, proporcionalmente aos votos de cada candidato ou agremiação. Partidos neutros não mudam.", BODY),
    ("3. Câmara: cadeiras recalculadas com quociente eleitoral, cláusulas de 10%/80%/20% e 3ª fase das sobras sem cláusula (decisão do STF). Dentro de cada agremiação os votos dos candidatos são escalados igualmente, então a ordem interna não muda.", BODY),
    ("4. Senado: duas vagas por UF, ganham os dois mais votados após a transferência.", BODY),
    ("", BODY),
    ("Cenários", BOLD),
    ("restrito_uf (principal): campo L = coligação de Lula no 1º turno (PT, PCdoB, PV, PSB, PDT, PSOL, Rede); campo F = coligação de Flávio (só PL). Swing de cada UF.", BODY),
    ("amplo_uf: campo F também inclui Novo, Missão, PP, União e Republicanos. Classificação minha, não oficial. Swing de cada UF.", BODY),
    ("restrito_nacional: como o principal, mas com o mesmo swing nacional (+2,80 p.p.) em todas as UFs.", BODY),
    ("Senado: candidato de partido do campo L é L; do PL é F; senão vale a coligação (com PT = L, com PL = F); no amplo, os partidos extras também viram F.", BODY),
    ("", BODY),
    ("Limitações", BOLD),
    ("Parte da virada veio de eleitores que se abstiveram no 1º turno (abstenção caiu de 21,08% para 19,21%) e dos votos dos outros presidenciáveis. Esses eleitores já tinham votado (ou não) para deputado e senador, e muita gente divide o voto entre presidente e Legislativo. A simulação assume que a variação se transmitiria inteira para o Legislativo, então tende a superestimar o efeito.", BODY),
    ("Os números simulados (cadeiras) são valores calculados em Python (scripts não incluídos aqui); as diferenças e o swing são fórmulas nesta planilha.", NOTE),
    ("", BODY),
    ("Abas", BOLD),
    ("Câmara bancadas: real x cenários por partido | Senado margem: quanto swing faltou para virar cada vaga | Swing por UF | Câmara mudanças por UF | Senado simulação e Câmara agremiações: resultado detalhado | Dados *: dados brutos do TSE", BODY),
]
for i, (t, f) in enumerate(linhas, 1):
    c = ws.cell(row=i, column=1, value=t)
    c.font = f
    c.alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width = 130

# ---------------- Câmara bancadas ----------------
tab = pd.read_csv(RES / "camara_bancadas_real_vs_simulado.csv", index_col=0)
tab = tab[["real", "restrito_uf", "amplo_uf", "restrito_nacional"]].reset_index()
tab.columns = ["partido", "real", "restrito_uf", "amplo_uf", "restrito_nacional"]
L = {"PT", "PCDOB", "PV", "PSB", "PDT", "PSOL", "REDE"}
tab["campo (coligação 1º turno)"] = tab.partido.map(lambda p: "Lula" if p in L else ("Flávio" if p == "PL" else "outros"))
ws = wb.create_sheet("Câmara bancadas")
end = write_table(ws, tab)
n = len(tab)
ws.cell(row=1, column=7, value="dif restrito_uf").font = HDR_FONT
ws.cell(row=1, column=8, value="dif amplo_uf").font = HDR_FONT
ws.cell(row=1, column=9, value="dif restrito_nacional").font = HDR_FONT
for col in (7, 8, 9):
    ws.cell(row=1, column=col).fill = HDR_FILL
    ws.column_dimensions[get_column_letter(col)].width = 14
for r in range(2, n + 2):
    for col, src in ((7, "C"), (8, "D"), (9, "E")):
        c = ws.cell(row=r, column=col, value=f"={src}{r}-$B{r}")
        c.font, c.number_format = BODY, "+0;-0;0"
tr = n + 2
ws.cell(row=tr, column=1, value="TOTAL").font = BOLD
for col in range(2, 10):
    L_ = get_column_letter(col)
    if col == 6:
        continue
    c = ws.cell(row=tr, column=col, value=f"=SUM({L_}2:{L_}{n + 1})")
    c.font = BOLD
r0 = tr + 2
ws.cell(row=r0, column=1, value="Blocos").font = BOLD
for k, (nome, crit) in enumerate((("Campo Lula (coligação)", "Lula"), ("PL", "Flávio"), ("Outros", "outros"))):
    rr = r0 + 1 + k
    ws.cell(row=rr, column=1, value=nome).font = BODY
    for col in range(2, 10):
        if col == 6:
            continue
        L_ = get_column_letter(col)
        c = ws.cell(row=rr, column=col, value=f'=SUMIF($F$2:$F${n + 1},"{crit}",{L_}2:{L_}{n + 1})')
        c.font = BODY
        if col >= 7:
            c.number_format = "+0;-0;0"
ws.cell(row=r0 + 5, column=1, value="Maioria simples da Câmara: 257 | quórum de PEC: 308").font = NOTE
ws.auto_filter.ref = None

# ---------------- Senado margem ----------------
m = pd.read_csv(RES / "senado_swing_necessario.csv", keep_default_na=False)
m = m[m.cenario == "restrito_uf"].copy()
m["swing_necessario_pp"] = pd.to_numeric(m.swing_necessario_pp, errors="coerce")
m = m.sort_values("swing_necessario_pp", na_position="last")
m = m[["uf", "eleitos", "vagas_L_reais", "swing_real_pp", "swing_necessario_pp"]]
m.columns = ["UF", "eleitos (real)", "vagas do campo Lula (real)", "swing real (p.p.)", "swing necessário p/ +1 vaga (p.p.)"]
ws = wb.create_sheet("Senado margem")
ws.cell(row=1, column=1, value="Quanto swing (cenário restrito_uf) o campo de Lula precisaria para ganhar mais uma vaga em cada UF. Vazio = campo de Lula já levou as duas vagas; inf = não vira com nenhum swing plausível.").font = NOTE
end = write_table(ws, m, start_row=2, numfmt={"swing real (p.p.)": "0.00", "swing necessário p/ +1 vaga (p.p.)": "0.00"})
ws.cell(row=2, column=6, value="faltou (p.p.)").font = HDR_FONT
ws.cell(row=2, column=6).fill = HDR_FILL
ws.column_dimensions["F"].width = 14
for r in range(3, end + 1):
    c = ws.cell(row=r, column=6, value=f'=IF(ISNUMBER(E{r}),E{r}-D{r},"")')
    c.font, c.number_format = BODY, "0.00"
    if r == 3:
        for col in range(1, 7):
            ws.cell(row=r, column=col).fill = HL

# ---------------- Swing por UF ----------------
sw = pd.read_csv(RES / "swing_por_uf.csv")
sw = sw[["uf", "lula_1t", "flavio_1t", "lula_2t", "flavio_2t"]]
ws = wb.create_sheet("Swing por UF")
end = write_table(ws, sw)
for col, h in ((6, "Lula % bipartidário 1T"), (7, "Lula % bipartidário 2T"), (8, "swing (p.p.)")):
    c = ws.cell(row=1, column=col, value=h)
    c.font, c.fill = HDR_FONT, HDR_FILL
    c.alignment = Alignment(wrap_text=True)
    ws.column_dimensions[get_column_letter(col)].width = 16
for r in range(2, end + 1):
    ws.cell(row=r, column=6, value=f"=B{r}/(B{r}+C{r})").number_format = "0.00%"
    ws.cell(row=r, column=7, value=f"=D{r}/(D{r}+E{r})").number_format = "0.00%"
    ws.cell(row=r, column=8, value=f"=(G{r}-F{r})*100").number_format = "+0.00;-0.00"
    for col in (6, 7, 8):
        ws.cell(row=r, column=col).font = BODY
ws.cell(row=end + 2, column=1, value="BR = Brasil; ZZ = exterior. Fonte: TSE.").font = NOTE

# ---------------- Câmara mudanças por UF ----------------
a = pd.read_csv(RES / "camara_simulacao_agremiacoes.csv", keep_default_na=False)
for c_ in ("vagas_restrito_uf", "vagas_amplo_uf", "vagas_restrito_nacional",
           "votos_restrito_uf", "votos_amplo_uf", "votos_restrito_nacional"):
    a[c_] = a[c_].astype(float).astype(int)
mud = a[(a.vagas_restrito_uf != a.vagas_oficial) | (a.vagas_amplo_uf != a.vagas_oficial)]
mud = mud[["uf", "agremiacao", "vagas_oficial", "vagas_restrito_uf", "vagas_amplo_uf", "vagas_restrito_nacional"]]
ws = wb.create_sheet("Câmara mudanças UF")
write_table(ws, mud.sort_values(["uf", "agremiacao"]))

# ---------------- Detalhes ----------------
s = pd.read_csv(RES / "senado_simulacao.csv", keep_default_na=False)
cols = ["uf", "candidato", "partido", "composicao_coligacao", "votos", "eleito",
        "campo_restrito_uf", "votos_restrito_uf", "eleito_restrito_uf",
        "campo_amplo_uf", "votos_amplo_uf", "eleito_amplo_uf",
        "votos_restrito_nacional", "eleito_restrito_nacional"]
s = s[cols].copy()
for c_ in ("votos_restrito_uf", "votos_amplo_uf", "votos_restrito_nacional"):
    s[c_] = s[c_].astype(float).astype(int)
for c_ in ("eleito", "eleito_restrito_uf", "eleito_amplo_uf", "eleito_restrito_nacional"):
    s[c_] = s[c_].astype(str).map({"True": "sim", "False": ""})
s = s.sort_values(["uf", "votos"], ascending=[True, False])
ws = wb.create_sheet("Senado simulação")
write_table(ws, s, widths={"composicao_coligacao": 45})

ag = a[["uf", "agremiacao", "votos", "vagas_oficial", "campo_restrito_uf", "votos_restrito_uf", "vagas_restrito_uf",
        "campo_amplo_uf", "votos_amplo_uf", "vagas_amplo_uf", "votos_restrito_nacional", "vagas_restrito_nacional"]]
ws = wb.create_sheet("Câmara agremiações")
write_table(ws, ag.sort_values(["uf", "votos"], ascending=[True, False]))

# ---------------- Dados brutos ----------------
for nome, arq in (("Dados presidente", "presidente_por_uf_1t_2t.csv"),
                  ("Dados senado", "senado_candidatos_2026.csv"),
                  ("Dados câmara partidos", "camara_partidos_2026.csv"),
                  ("Dados câmara candidatos", "camara_candidatos_2026.csv")):
    df = pd.read_csv(DATA / arq, keep_default_na=False)
    ws = wb.create_sheet(nome)
    write_table(ws, df)

wb.save(OUTF)
print("ok", OUTF)
