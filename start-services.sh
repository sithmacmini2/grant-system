#!/bin/bash
# Grant Intelligence System - Start Services
# Run this to start the Telegram bot for command handling

echo "Starting Grant Intelligence System services..."

SERVICE_NAME=grants-telegram-bot.service

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "TELEGRAM_BOT_TOKEN is not set. Export it before starting the bot."
    exit 1
fi

# Check if already running
if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    echo "Telegram bot is already running"
else
    echo "Starting Telegram bot..."
    systemctl --user start "$SERVICE_NAME"
    if ! systemctl --user is-active --quiet "$SERVICE_NAME"; then
        echo "Telegram bot failed to start. Recent service log:"
        journalctl --user -u "$SERVICE_NAME" -n 20 --no-pager
        exit 1
    fi
    echo "Telegram bot started"
fi

echo ""
echo "Services running:"
echo "  Telegram bot: Active (send commands to @SithNPO_bot)"
echo "  View grants: /home/sithmm2_admin/wiki/Grants/2026/"
echo ""
echo "To stop: systemctl --user stop $SERVICE_NAME"
