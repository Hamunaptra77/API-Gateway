#!/bin/bash
# Install automatic Let's Encrypt renewal via cron

CRON_JOB="0 3 * * 0 cd /home/ki-projekt/api-gateway && ./certbot-renew.sh deine-domain.de >> /var/log/certbot-renew.log 2>&1"
CRON_USER="root"

echo "🔧 Setting up automatic Let's Encrypt renewal via cron..."

# Check if cron is available
if ! command -v crontab &> /dev/null; then
  echo "❌ crontab not found. Installing..."
  apt-get update && apt-get install -y cron
fi

# Create log file
sudo touch /var/log/certbot-renew.log
sudo chmod 666 /var/log/certbot-renew.log

# Check if job already exists
if crontab -l 2>/dev/null | grep -q "certbot-renew.sh"; then
  echo "⚠️  Cron job already exists"
  crontab -l | grep certbot-renew
else
  # Add cron job
  (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
  echo "✅ Cron job installed:"
  echo "   $CRON_JOB"
  echo ""
  echo "📋 Next renewal attempt: Every Sunday at 3:00 AM"
  echo "📝 Log file: /var/log/certbot-renew.log"
fi

# Show current cron jobs
echo ""
echo "Current cron jobs:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "(none)"

