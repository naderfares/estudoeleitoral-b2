#!/bin/bash
# Baixa JSONs de resultado do TSE (eleição 2026) para todas as UFs
OUT=/Users/nader/workspace/personal/estudoeleitoral/analise/tse_raw/api
B=https://resultados.tse.jus.br/oficial/ele2026
UFS="ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to"
get() { # eleicao cargo uf
  local f="$3-c$2-e00$1-u.json"
  [ -s "$OUT/$f" ] && return
  curl -sS -m 60 --retry 3 -o "$OUT/$f" -w "$f %{http_code} %{size_download}\n" "$B/$1/dados/$3/$f"
}
for uf in br zz $UFS; do get 6257 0001 $uf; get 6258 0001 $uf; done
for uf in $UFS; do get 6259 0005 $uf; get 6259 0006 $uf; done
