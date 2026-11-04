"""Planilha v3 = v2 + abas de validação dos comportamentos."""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

V2, R3, OUTF = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
F = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
BODY = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
TITLE = Font(name=F, size=13, bold=True)
NOTE = Font(name=F, size=9, italic=True, color="555555")
HL = PatternFill("solid", fgColor="FFF2CC")
wb = load_workbook(V2)


def table(ws, df, r0=1, widths=None, numfmt=None):
    numfmt = numfmt or {}
    for j, c in enumerate(df.columns, 1):
        x = ws.cell(row=r0, column=j, value=str(c))
        x.font, x.fill = HDR_FONT, HDR_FILL
        x.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(df.itertuples(index=False), r0 + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            if hasattr(v, "item"):
                v = v.item()
            x = ws.cell(row=i, column=j, value=v)
            x.font = BODY
            x.alignment = Alignment(wrap_text=isinstance(v, str) and len(v) > 40, vertical="top")
            col = df.columns[j - 1]
            if col in numfmt:
                x.number_format = numfmt[col]
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                x.number_format = "#,##0"
    for j, c in enumerate(df.columns, 1):
        w = (widths or {}).get(c)
        if w is None:
            w = min(max([len(str(c))] + [len(str(x)) for x in df[c].head(200)]) + 2, 40)
        ws.column_dimensions[get_column_letter(j)].width = w
    return r0 + len(df)


def text(ws, r, t, f=BODY, width=None):
    x = ws.cell(row=r, column=1, value=t)
    x.font = f
    x.alignment = Alignment(wrap_text=True, vertical="top")
    if width:
        ws.column_dimensions["A"].width = width


real = pd.read_csv(R3 / "real.csv", index_col=0).iloc[:, 0]
sens = pd.read_csv(R3 / "sensibilidade_comportamentos.csv")
pv = pd.read_csv(R3 / "ponto_de_virada.csv")
mc = pd.read_csv(R3 / "monte_carlo.csv")
flips = pd.read_csv(R3 / "monte_carlo_senado_trocas.csv")
imp = pd.read_csv(R3 / "monte_carlo_importancia.csv", index_col=0)
teto = pd.read_csv(R3 / "teto_absoluto.csv")
geo = pd.read_csv(R3 / "geo_evidencia.csv")
geoc = pd.read_csv(R3 / "geo_correlacoes.csv")
q = mc[["PL", "PT", "colig", "outros", "sen_L", "sen_F", "sen_N"]].quantile([0.05, 0.5, 0.95])

# ================= Validação: resumo =================
ws = wb.create_sheet("Validação resumo", 1)
t20 = teto[(teto.n0 == 20)].iloc[0]
rj_ok = (mc.RJ_jordy_menos_benedita > 0).mean() * 100
linhas = [
    ("Validação da lógica: todos os comportamentos possíveis (versão 3)", TITLE),
    ("", BODY),
    ("Pergunta testada: quem foi votar no 2º turno (manifestações, mobilização) tende a votar na esquerda para o Congresso, mas não necessariamente. E os demais grupos? Testei cada comportamento possível de cada grupo de eleitores que mudou entre os turnos, sozinho e combinado.", BODY),
    ("", BODY),
    ("O que foi feito", BOLD),
    ("1. Matriz de grupos x comportamentos (aba Comportamentos testados): 9 grupos de eleitores, 13 parâmetros, cada um com faixa de valores possíveis.", BODY),
    ("2. Um fator por vez (aba Teste um fator): cada comportamento levado ao extremo, mantendo o resto no caso-base.", BODY),
    ("3. Cenários combinados e teto absoluto (aba Cenários combinados).", BODY),
    ("4. Ponto de virada (aba Ponto de virada): quanto os mobilizados teriam de pender à esquerda para mudar as conclusões.", BODY),
    (f"5. Monte Carlo (aba Monte Carlo): {len(mc):,} combinações sorteadas dentro de faixas plausíveis de todos os parâmetros.".replace(",", "."), BODY),
    ("6. Evidência geográfica (aba Evidência geográfica): onde a mobilização aconteceu e como votam os eleitores de Lula dessas zonas.", BODY),
    ("", BODY),
    ("Resultados", BOLD),
    (f"Real: PL {int(real.PL)}, coligação Lula {int(real.colig)}; Senado (54 eleitos): campo Lula {int(real.sen_L)}, campo Flávio {int(real.sen_F)}, outros {int(real.sen_N)}.", BODY),
    ("Caso-base (versão 2): PL 118, coligação Lula 125; Senado sem mudança entre campos, exceto o empate técnico no RN.", BODY),
    (f"Monte Carlo, 90% das combinações: PL entre {int(q.loc[0.05,'PL'])} e {int(q.loc[0.95,'PL'])}; coligação Lula entre {int(q.loc[0.05,'colig'])} e {int(q.loc[0.95,'colig'])}; campo Lula no Senado entre {int(q.loc[0.05,'sen_L'])} e {int(q.loc[0.95,'sen_L'])}; campo Flávio no Senado fica em {int(q.loc[0.5,'sen_F'])}. Jordy (PL) fica à frente de Benedita (PT) no RJ em {rj_ok:.0f}% das combinações.", BODY),
    ("Inclinação dos mobilizados (sua hipótese): é o fator que mais pesa (correlação 0,8 com as cadeiras da esquerda), mas o efeito é limitado porque eles são ~2,4 milhões. Do 'sem viés nenhum' ao '100% esquerda', a coligação de Lula vai de 123 a 130 cadeiras e o PL de 120 a 118.", BODY),
    ("Evidência: em 22 das 27 UFs a mobilização foi maior onde os eleitores de Lula votam mais na esquerda para deputado (correlação mediana 0,19). A tendência existe, mas é fraca: incorporá-la muda o voto dos novos eleitores na esquerda de 51,1% para 52,0%.", BODY),
    (f"Teto absoluto (todo o ganho de Lula viria de novos eleitores, todos votando 100% na esquerda): PL {int(t20.PL)}, coligação Lula {int(t20.colig)}, campo Lula no Senado {int(t20.sen_L)}; Benedita venceria no RJ. Esse cenário contradiz os dados: o comparecimento líquido cresceu 2,9 milhões, não os 10,8 milhões que ele exige.", BODY),
    ("O que realmente mudaria o quadro é outra pergunta: se o clima do 2º turno mudasse o voto legislativo dos eleitores FIÉIS (108 milhões que não mudaram o voto para presidente). 10% do voto de centro dos fiéis de Lula indo para a esquerda daria +21 cadeiras à coligação; se a polarização valesse para os dois lados, PL e esquerda cresceriam juntos às custas do centro. Não há dado que sustente nem descarte isso, porque esse eleitorado não mudou de comportamento observável.", BODY),
    ("", BODY),
    ("Conclusão", BOLD),
    ("Dentro de qualquer combinação de comportamentos compatível com os dados, a lógica se sustenta: o PL perderia de 1 a 5 cadeiras, a esquerda ganharia de 0 a 7, parte das cadeiras do PL iria para o centro, e o Senado ficaria praticamente igual (só empates técnicos mudam). Resultados muito diferentes exigem ou um fluxo de eleitores que contradiz os dados ou uma mudança de comportamento de quem não mudou de voto.", BODY),
]
for i, (t, f) in enumerate(linhas, 1):
    text(ws, i, t, f)
ws.column_dimensions["A"].width = 150

# ================= Comportamentos testados =================
mat = pd.DataFrame([
    ("Fiéis: Lula 1T -> Lula 2T", 53.14, "Mantêm o voto legislativo real", "Clima: parte do voto de centro migra para a esquerda (tau_L 10% e 25%)", "Nenhuma: voto para presidente não mudou; voto legislativo sob outro clima não é observável"),
    ("Fiéis: Flávio 1T -> Flávio 2T", 55.30, "Mantêm o voto legislativo real", "Clima: parte do voto de centro migra para o PL (tau_F 10%)", "Idem"),
    ("Novos eleitores: abstenção 1T -> Lula 2T", 2.41, "Votam como o eleitor típico de Lula da sua UF", "Sem viés (como eleitor médio da UF); mais à esquerda; 100% esquerda; só votam para presidente (roll-off 30%/60%); votam como os vizinhos das zonas de mobilização; ganho todo para PT", "Mobilização um pouco maior onde eleitores de Lula votam mais à esquerda (22 de 27 UFs, correlação mediana 0,19)"),
    ("Novos eleitores: abstenção 1T -> Flávio 2T", 0.76, "Votam como o eleitor típico de Flávio da UF", "Sem viés; 100% PL; roll-off; geografia", "Idem (simétrico)"),
    ("Novos eleitores: abstenção 1T -> branco/nulo 2T", 0.93, "Perfil de quem vota branco/nulo (majoritariamente branco/nulo)", "Grupo pequeno, efeito desprezível", "-"),
    ("Outros presidenciáveis 1T -> Lula 2T", 4.19, "Mantêm o voto legislativo real", "Metade ou todos adotam o perfil dos eleitores de Lula (arrasto); parte era, na verdade, abstenção 1T (reclassificação nu)", "Perfil real desse grupo não é estimável com confiança (oscila 0%-100% entre UFs)"),
    ("Outros presidenciáveis 1T -> Flávio 2T", 3.60, "Mantêm o voto legislativo real", "Metade ou todos adotam o perfil dos eleitores de Flávio", "Idem"),
    ("Branco/nulo 1T -> Lula 2T", 4.20, "Mantêm o voto legislativo real (parte é erro na urna de 6 cargos)", "Metade ou todos passam a votar como eleitores de Lula; parte era abstenção 1T (reclassificação mu)", "Branco/nulo caiu de 6,0 para 4,1 mi entre turnos; padrão compatível com cédula mais simples no 2º turno"),
    ("Trocaram de lado (Flávio <-> Lula)", 0.11, "Trocam o perfil legislativo", "Mantêm o voto legislativo", "Grupo muito pequeno"),
    ("Votaram no 1T e faltaram no 2T", 1.18, "Mantêm o voto legislativo real (votaram de fato)", "Perdem o voto legislativo (demob)", "Faltar no 2º turno se concentra onde não houve disputa estadual"),
    ("Incerteza estatística da estimativa", None, "Âncora N0 = 20", "N0 = 0 e N0 = 100", "-"),
], columns=["grupo de eleitores", "tamanho (milhões)", "hipótese do caso-base", "comportamentos alternativos testados", "evidência disponível"])
ws = wb.create_sheet("Comportamentos testados", 2)
table(ws, mat, widths={"grupo de eleitores": 38, "tamanho (milhões)": 11, "hipótese do caso-base": 40,
                       "comportamentos alternativos testados": 60, "evidência disponível": 55}, numfmt={"tamanho (milhões)": "0.00"})

# ================= Teste um fator =================
cols = ["grupo", "descricao", "parametro", "valor", "PL", "PT", "colig", "outros", "sen_L", "sen_F", "sen_N", "RJ_jordy_menos_benedita", "sen_flips"]
s1 = sens[cols].copy()
s1["RJ_jordy_menos_benedita"] = s1.RJ_jordy_menos_benedita.round().astype(int)
s1 = pd.concat([pd.DataFrame([dict(grupo="real", descricao="Resultado oficial", parametro="-", valor="-", PL=int(real.PL), PT=int(real.PT),
                                    colig=int(real.colig), outros=int(real.outros), sen_L=int(real.sen_L), sen_F=int(real.sen_F),
                                    sen_N=int(real.sen_N), RJ_jordy_menos_benedita=691640, sen_flips="-")]), s1], ignore_index=True)
s1.columns = ["tipo", "comportamento testado", "parâmetro", "valor", "PL", "PT", "coligação Lula", "centro e demais",
              "Senado: campo Lula", "Senado: campo Flávio", "Senado: outros", "RJ: Jordy menos Benedita (votos)", "Senado: vagas que mudam"]
oat = s1[s1.tipo.isin(["real", "caso-base", "um fator por vez"])]
ws = wb.create_sheet("Teste um fator", 3)
end = table(ws, oat, widths={"comportamento testado": 60, "Senado: vagas que mudam": 70, "tipo": 14})
for r in range(2, end + 1):
    if ws.cell(row=r, column=1).value in ("real", "caso-base"):
        for c in range(1, 14):
            ws.cell(row=r, column=c).fill = HL
ws.freeze_panes = "C2"

# ================= Cenários combinados =================
comb = s1[s1.tipo.isin(["real", "caso-base", "cenário combinado"])].copy()
tt = teto[teto.n0 == 20].copy()
add = pd.DataFrame(dict(tipo="teto teórico", **{"comportamento testado": tt.cenario, "parâmetro": "todo ganho de Lula = novos eleitores, 100% esquerda",
                        "valor": "-", "PL": tt.PL, "PT": tt.PT, "coligação Lula": tt.colig, "centro e demais": tt.outros,
                        "Senado: campo Lula": tt.sen_L, "Senado: campo Flávio": tt.sen_F, "Senado: outros": tt.sen_N,
                        "RJ: Jordy menos Benedita (votos)": tt.RJ_jordy_menos_benedita.round().astype(int), "Senado: vagas que mudam": tt.sen_flips}))
comb = pd.concat([comb, add], ignore_index=True)
ws = wb.create_sheet("Cenários combinados", 4)
end = table(ws, comb, widths={"comportamento testado": 60, "parâmetro": 45, "Senado: vagas que mudam": 80, "tipo": 16})
ws.cell(row=end + 2, column=1, value="Teto teórico contradiz os dados: exigiria ~10,8 milhões de novos eleitores, mas o comparecimento líquido cresceu 2,9 milhões.").font = NOTE
ws.cell(row=end + 3, column=1, value="Cenários com 'clima' mudam o voto de quem não mudou de voto para presidente: é outra pergunta, sem dado que sustente ou descarte.").font = NOTE

# ================= Ponto de virada =================
p2 = pv.copy()
p2["RJ_jordy_menos_benedita"] = p2.RJ_jordy_menos_benedita.round().astype(int)
p2.columns = ["contexto", "inclinação dos mobilizados (alpha_L)", "PL", "PT", "coligação Lula", "centro e demais", "Senado: campo Lula",
              "Senado: campo Flávio", "Senado: outros", "RJ: Jordy menos Benedita (votos)", "Senado: vagas que mudam"]
ws = wb.create_sheet("Ponto de virada", 5)
text(ws, 1, "alpha_L: -1 = mobilizados pró-Lula votam como o eleitor médio da UF (sem viés); 0 = como o eleitor típico de Lula da UF; +1 = 100% dos votos válidos na coligação de Lula.", NOTE)
table(ws, p2, r0=2, widths={"contexto": 42, "Senado: vagas que mudam": 70}, numfmt={"inclinação dos mobilizados (alpha_L)": "+0.00;-0.00;0"})

# ================= Monte Carlo =================
ws = wb.create_sheet("Monte Carlo", 6)
text(ws, 1, f"{len(mc):,} combinações sorteadas de todos os parâmetros dentro de faixas plausíveis (sem 'clima', que muda a pergunta).".replace(",", "."), BOLD)
faixas = pd.DataFrame([
    ("alpha_L", "inclinação dos novos eleitores de Lula", "-1 a +0,6"), ("rho", "roll-off (só votam para presidente)", "0 a 30%"),
    ("alpha_F", "inclinação dos novos eleitores de Flávio", "-1 a +0,6"), ("geo", "perfil pela geografia da mobilização", "sim/não (50%)"),
    ("lam_O", "arrasto sobre eleitores dos outros presidenciáveis", "0 a 50%"), ("lam_BN", "branco/nulo 1T que mudaria o voto legislativo", "0 a 50%"),
    ("mu", "branco/nulo -> Lula reclassificado como abstenção", "0 a 50%"), ("nu", "outros -> Lula reclassificado como abstenção", "0 a 50%"),
    ("demob", "faltou no 2º turno perde voto legislativo", "sim em 20%"), ("lam_S", "efeito sobre quem trocou de lado", "0 a 100%"),
    ("kappa", "ganho da esquerda concentrado no PT", "0 a 50%"), ("n0", "âncora estatística", "0, 20 ou 100"),
], columns=["parâmetro", "significado", "faixa sorteada"])
end = table(ws, faixas, r0=2, widths={"parâmetro": 12, "significado": 50, "faixa sorteada": 18})
r = end + 2
text(ws, r, "Distribuição dos resultados", BOLD)
qq = mc[["PL", "PT", "colig", "outros", "sen_L", "sen_F", "sen_N", "RJ_jordy_menos_benedita"]].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
qq = qq[["min", "5%", "25%", "50%", "75%", "95%", "max"]].round(0).astype(int).reset_index()
qq["index"] = qq["index"].map({"PL": "PL", "PT": "PT", "colig": "coligação Lula", "outros": "centro e demais", "sen_L": "Senado: campo Lula",
                               "sen_F": "Senado: campo Flávio", "sen_N": "Senado: outros", "RJ_jordy_menos_benedita": "RJ: Jordy menos Benedita (votos)"})
qq.insert(1, "real", [int(real.PL), int(real.PT), int(real.colig), int(real.outros), int(real.sen_L), int(real.sen_F), int(real.sen_N), 691640])
qq = qq.rename(columns={"index": "resultado"})
end = table(ws, qq, r0=r + 1)
r = end + 2
text(ws, r, "Frequência de cada mudança no Senado (% das combinações)", BOLD)
fl = flips.rename(columns={flips.columns[0]: "mudança", "pct": "% das combinações"})
fl["% das combinações"] = fl["% das combinações"] / 100
end = table(ws, fl, r0=r + 1, widths={"mudança": 55}, numfmt={"% das combinações": "0.0%"})
r = end + 2
text(ws, r, "O que mais pesa: correlação entre cada parâmetro e as cadeiras", BOLD)
im = imp.reset_index().rename(columns={"index": "parâmetro", "colig": "coligação Lula", "outros": "centro e demais"})
table(ws, im, r0=r + 1, numfmt={"PL": "+0.00;-0.00", "coligação Lula": "+0.00;-0.00", "centro e demais": "+0.00;-0.00"})
ws.column_dimensions["A"].width = 55

# ================= Evidência geográfica =================
ws = wb.create_sheet("Evidência geográfica", 7)
text(ws, 1, "A mobilização do 2º turno foi maior onde os eleitores de Lula votam mais na esquerda para deputado?", BOLD)
text(ws, 2, "Correlação, dentro de cada UF e entre zonas eleitorais, entre o crescimento do comparecimento (2T - 1T) e a razão votos da coligação de Lula para deputado / votos de Lula. Positiva = mobilização maior onde o eleitor de Lula vota mais à esquerda.", NOTE)
gc = geoc.rename(columns={"SG_UF": "UF", "corr_mob_esq_por_lula": "correlação mobilização x esquerda entre eleitores de Lula",
                          "corr_mob_lula": "correlação mobilização x força de Lula", "n": "zonas"}).sort_values("correlação mobilização x esquerda entre eleitores de Lula")
end = table(ws, gc, r0=3, numfmt={"correlação mobilização x esquerda entre eleitores de Lula": "+0.00;-0.00", "correlação mobilização x força de Lula": "+0.00;-0.00", "zonas": "0"})
r = end + 1
text(ws, r, "Mediana (fórmula):", BOLD)
ws.cell(row=r, column=2, value=f"=MEDIAN(B4:B{end})").number_format = "+0.00;-0.00"
ws.cell(row=r + 1, column=1, value="UFs com correlação positiva:").font = BOLD
ws.cell(row=r + 1, column=2, value=f'=COUNTIF(B4:B{end},">0")')
r += 3
text(ws, r, "Perfil dos novos eleitores de Lula: eleitor típico de Lula da UF x vizinhos das zonas onde a mobilização aconteceu", BOLD)
g2 = geo[["uf", "novos_lula", "base_colig", "geo_colig", "base_PL", "geo_PL", "base_centro", "geo_centro"]].sort_values("novos_lula", ascending=False)
g2["novos_lula"] = g2.novos_lula.round().astype(int)
g2.columns = ["UF", "novos eleitores de Lula", "esquerda: típico", "esquerda: geográfico", "PL: típico", "PL: geográfico", "centro: típico", "centro: geográfico"]
end = table(ws, g2, r0=r + 1, numfmt={c: "0.0%" for c in g2.columns[2:]})
ws.cell(row=end + 1, column=1, value="Brasil (média ponderada)").font = BOLD
for j in range(3, 9):
    L = get_column_letter(j)
    c = ws.cell(row=end + 1, column=j, value=f"=SUMPRODUCT($B${r + 2}:$B${end},{L}{r + 2}:{L}{end})/SUM($B${r + 2}:$B${end})")
    c.number_format, c.font = "0.0%", BOLD
ws.column_dimensions["A"].width = 26

# Leia-me: nota da v3
lm = wb["Leia-me"]
r = lm.max_row + 2
lm.cell(row=r, column=1, value="Versão 3: abas 'Validação resumo' a 'Evidência geográfica' testam todos os comportamentos possíveis dos grupos de eleitores (sozinhos, combinados e em 3.000 combinações sorteadas).").font = BOLD
wb.save(OUTF)
print("ok", OUTF)
