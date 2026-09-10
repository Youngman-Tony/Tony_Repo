#!/bin/bash
set -e

echo "=== Обновление пакетов и установка зависимостей ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "=== Клонирование репозитория ==="
cd /opt
rm -rf auction_bot
git clone https://github.com/Youngman-Tony/Tony_Repo.git auction_bot
cd auction_bot

echo "=== Создание виртуального окружения ==="
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "=== Создание .env ==="
cat > .env << 'EOF'
BOT_TOKEN=8905887181:AAEsuF7B5hF2e-QmWTVYtQSILSYGtVamNcA
BOT_USERNAME=Tony_auction_bot
EOF

echo "=== Создание systemd-сервиса ==="
cat > /etc/systemd/system/auction-bot.service << 'EOF'
[Unit]
Description=Auction Bot (Tony)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/auction_bot
EnvironmentFile=/opt/auction_bot/.env
ExecStart=/opt/auction_bot/venv/bin/python /opt/auction_bot/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable auction-bot
systemctl start auction-bot

echo "=== Статус сервиса ==="
sleep 3
systemctl status auction-bot --no-pager || true
echo ""
echo "=== Логи ==="
journalctl -u auction-bot -n 20 --no-pager || true