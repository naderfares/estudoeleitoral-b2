#!/bin/bash
# roda estimação + contrafactual para vários N0
cd /Users/nader/workspace/personal/estudoeleitoral/analise
for n0 in 0 20 100; do
  python3 -I -W ignore scripts/ei.py munzona results2_n0_$n0 $n0 > /dev/null 2>&1
  python3 -I -W ignore scripts/cf.py results2_n0_$n0 data munzona results > results2_n0_$n0/cf_log.txt 2>&1
  echo "== N0=$n0"; sed -n '1,4p;/Coligação Lula/p;/SENADO/,$p' results2_n0_$n0/cf_log.txt
done
