#!/bin/bash
# Codespace の中で、説明資料から抜き出した手順（steps_hN.json）を順に流す（リハーサル。2026-11-11）
# 使い方: bash .rh/run_all.sh 3 4 5 6 8 9
R=$(cd "$(dirname "$0")" && pwd); OUT=$R/out; mkdir -p $OUT
command -v python3 >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq python3 >/dev/null; }
rm -rf /tmp/rhdist && mkdir -p /tmp/rhdist && tar xzf $R/dist.tgz -C /tmp/rhdist
{ docker version; docker compose version; docker info 2>/dev/null | grep -E "Server Version|Storage Driver|Total Memory|CPUs"; } > $OUT/env.txt 2>&1
for N in "$@"; do
  P=$((N-1)); [ $N = 3 ] && P=1
  docker rm -f $(docker ps -aq) >/dev/null 2>&1; docker volume prune -af >/dev/null 2>&1; docker network prune -f >/dev/null 2>&1
  W=/workspaces/rhw/h$N; rm -rf $W ~/team-board; mkdir -p $W; cp -r "/tmp/rhdist/完成コード/ハンズオン${P}の完成/hitokoto" $W/hitokoto
  ( cd $W && timeout 2400 python3 -W ignore $R/rh.py run $R/steps_h$N.json --os mac --work $W/hitokoto --dist /tmp/rhdist --out $OUT/result_h$N.json > $OUT/log_h$N.txt 2>&1 )
  { docker ps -a; for c in $(docker ps -aq); do echo "=== $c"; docker logs --tail 60 $c; done; } > $OUT/dockerlogs_h$N.txt 2>&1
  ls -laR $W/hitokoto > $OUT/files_h$N.txt 2>&1; umask >> $OUT/files_h$N.txt
  echo "H$N: $(grep -c '^\[OK\]' $OUT/log_h$N.txt) OK / $(grep -c '^\[NG\]' $OUT/log_h$N.txt) NG / $(grep -c '^\[WARN\]' $OUT/log_h$N.txt) WARN" >> $OUT/summary.txt
done
docker rm -f $(docker ps -aq) >/dev/null 2>&1
ls -laR /workspaces/hitokoto-v2-rehearsal | grep -v "\.git" | head -60 > $OUT/files_checkout.txt; getfacl /workspaces /workspaces/hitokoto-v2-rehearsal >> $OUT/files_checkout.txt 2>&1
echo DONE >> $OUT/summary.txt
