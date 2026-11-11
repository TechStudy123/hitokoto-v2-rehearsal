#!/bin/bash
# Docker Hub が要る手順（H1 の login・H7 の push／pull／エラー・H8 の Scout）を Codespace で確かめる。DH_USER・DH_TOKEN を環境変数で渡す
R=$(cd "$(dirname "$0")" && pwd); OUT=$R/out; mkdir -p $OUT; LOG=$OUT/log_hub.txt; : > $LOG
run() { echo "\$ $*" >> $LOG; timeout ${TO:-900} bash -c "$*" >> $LOG 2>&1; echo "[rc=$?]" >> $LOG; }
U=$DH_USER; REPO=hitokoto-rehearsal
run docker logout
run docker run hello-world
run "echo wrong-password | docker login -u $U --password-stdin"
run "printenv DH_TOKEN | docker login -u $U --password-stdin"
rm -rf /tmp/hub && mkdir -p /tmp/hub && cp -r "/tmp/rhdist/完成コード/ハンズオン6の完成/hitokoto" /tmp/hub/ && cd /tmp/hub/hitokoto
run docker build -q -t hitokoto:1.0 .
run docker tag hitokoto:1.0 $U/$REPO:1.0
run docker images
run docker push $U/$REPO:1.0
run docker push hitokoto:1.0
run docker rmi $U/$REPO:1.0 hitokoto:1.0
run docker run -d --name app -p 8000:8000 -e DB_HOST=none $U/$REPO:1.0
sleep 5; run "curl -s localhost:8000 | grep footer"; run docker rm -f app
cp "/tmp/rhdist/完成コード/ハンズオン7の完成/hitokoto/templates/base.html" templates/
run docker build -q -t $U/$REPO:1.1 .; run docker push $U/$REPO:1.1
# H8
cp -r "/tmp/rhdist/完成コード/ハンズオン7の完成/hitokoto/." .
run docker build -q -t hitokoto:1.1 .
sed -i 's/^FROM python:3.15-slim$/FROM python:3.15/' Dockerfile; run docker build -q -t hitokoto:full .
cp -r "/tmp/rhdist/完成コード/ハンズオン8の完成/hitokoto/." .
run docker build -q -t hitokoto:2.0 .
run docker images hitokoto
run docker scout version
TO=300 run "curl -fsSL https://raw.githubusercontent.com/docker/scout-cli/main/install.sh -o install-scout.sh && sh install-scout.sh && rm install-scout.sh"
run docker scout version
for t in full 1.1 2.0; do TO=900 run docker scout quickview hitokoto:$t; done
TO=900 run docker scout cves hitokoto:2.0 --only-severity critical,high
run docker tag hitokoto:2.0 $U/$REPO:2.0; run docker push $U/$REPO:2.0
run docker system df
echo HUBDONE >> $LOG
