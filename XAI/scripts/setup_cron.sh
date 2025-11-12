#!/bin/bash
# Setup cron jobs for AIXN custody monitoring

echo "================================================================================"
echo "AIXN Exchange - Custody Monitoring Cron Setup"
echo "================================================================================"
echo ""

# Get the absolute path to the scripts directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AIXN_ROOT="$(dirname "$SCRIPT_DIR")"

echo "AIXN Root Directory: $AIXN_ROOT"
echo ""

# Create cron job entries
CRON_FILE="/tmp/aixn_cron_jobs.txt"

cat > "$CRON_FILE" << EOF
# AIXN Exchange Custody Monitoring Cron Jobs
# Generated: $(date)

# Daily custody monitor report (runs at 9 AM every day)
0 9 * * * cd $AIXN_ROOT && python3 scripts/custody_monitor.py >> custody_data/logs/monitor.log 2>&1

# Custody alerts check (runs every 4 hours)
0 */4 * * * cd $AIXN_ROOT && python3 scripts/custody_alerts.py >> custody_data/logs/alerts.log 2>&1

# Weekly custody summary (runs Sunday at 8 AM)
0 8 * * 0 cd $AIXN_ROOT && python3 scripts/custody_monitor.py > custody_data/reports/weekly_$(date +\%Y\%m\%d).txt 2>&1

EOF

echo "Cron job configuration:"
echo "--------------------------------------------------------------------------------"
cat "$CRON_FILE"
echo "--------------------------------------------------------------------------------"
echo ""

# Ask user to confirm
read -p "Do you want to install these cron jobs? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    # Install cron jobs
    (crontab -l 2>/dev/null | grep -v "# AIXN Exchange Custody"; cat "$CRON_FILE") | crontab -

    echo ""
    echo "Cron jobs installed successfully!"
    echo ""
    echo "Current crontab:"
    echo "--------------------------------------------------------------------------------"
    crontab -l
    echo "--------------------------------------------------------------------------------"
    echo ""
    echo "Log files will be saved to:"
    echo "  - Daily reports: $AIXN_ROOT/custody_data/logs/monitor.log"
    echo "  - Alerts: $AIXN_ROOT/custody_data/logs/alerts.log"
    echo "  - Weekly summaries: $AIXN_ROOT/custody_data/reports/weekly_*.txt"
    echo ""
else
    echo "Installation cancelled."
    echo "To manually install, run: crontab $CRON_FILE"
fi

# Create log directories
mkdir -p "$AIXN_ROOT/custody_data/logs"
mkdir -p "$AIXN_ROOT/custody_data/reports"
mkdir -p "$AIXN_ROOT/custody_data/alerts"

echo ""
echo "Log directories created."
echo ""
echo "Setup complete!"
echo ""
echo "To view cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove cron jobs: crontab -r"
echo ""
