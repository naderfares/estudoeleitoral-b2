# Análise B2 na nuvem (modelo bayesiano R×C)

Parte do estudo "Mobilização entre turnos e composição do Congresso: um contrafactual com dados do TSE para 2026", de Nader Abdel Jabbar ([ORCID 0009-0000-8746-5107](https://orcid.org/0009-0000-8746-5107)). Pré-registro: <https://doi.org/10.17605/OSF.IO/RTGA9>. Pacote de replicação completo: <https://doi.org/10.5281/zenodo.23936419>.

Este repositório tem só o necessário para rodar a análise complementar B2 no GitHub Actions: dados por município e zona, código congelado e os perfis da regressão de Goodman. Numa máquina de 2 núcleos a corrida levaria cerca de 84 horas; aqui ela é dividida em 54 tarefas (27 UFs × 2 tabelas) que rodam ao mesmo tempo.

## Como rodar

Na aba **Actions**, escolha "B2 - modelo bayesiano RxC" e clique em **Run workflow**. Pela linha de comando: `gh workflow run b2.yml`.

Ao final, o resultado fica no ramo `resultados-b2`:

- `analise/results_b2/bayes.csv`: placebo, curva de arrasto por braço e índice de H2 para cada um dos 200 sorteios da posteriori;
- `analise/results_b2/comparacao_fluxos_nacionais.csv`: fluxos nacionais, modelo bayesiano contra regressão de Goodman;
- `analise/results2_n0_bayes/diagnostico_bayes.csv`: R-hat, tamanho efetivo e divergências por UF e tabela;
- `analise/results2_n0_bayes/limites_duncan_davis.csv`: limites determinísticos.

## O que muda em relação ao script original

Nada no modelo. `scripts/b2_tabela.py` importa as funções de `scripts/ei_bayes.py` sem mudança e roda uma tabela de uma UF; `scripts/b2_juntar.py` monta os mesmos arquivos que `ei_bayes.py` gravaria. `scripts/teste_b2_pedacos.py` confere, com cadeias curtas, que os pedaços reproduzem `ei_bayes.py` byte a byte.
