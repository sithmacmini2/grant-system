#!/bin/bash
# Grant Intelligence System - Start Services
# Run this to start the Telegram bot for command handling

echo "Starting Grant Intelligence System services..."

# Check if already running
if pgrep -f "telegram-bot.py poll" > /dev/null; then
    echo "⚠️ Telegram bot is already running"
else
    echo "Starting Telegram bot..."
    cd /home/sithmm2_admin/grants-system/hermes-tasks
    nohup python3 telegram-bot.py poll > /home/sithmm2_admin/grants-system/logs/telegram-bot.log 2>&1 &
    echo "✅ Telegram bot started (PID: $!)"
fi

echo ""
echo "Services running:"
echo "  📱 Telegram bot: Active (send commands to @SithNPO_bot)"
echo "  📊 View grants: /home/sithmm2_admin/wiki/Grants/2026/"
echo ""
echo "To stop: pkill -f telegram-bot.py"