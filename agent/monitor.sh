#!/usr/bin/env bash
set -euo pipefail

read_cpu() {
  awk '/^cpu / { idle=$5+$6; total=0; for (i=2; i<=NF; i++) total+=$i; print total, idle; exit }' /proc/stat
}

read -r total_a idle_a < <(read_cpu)
sleep 1
read -r total_b idle_b < <(read_cpu)
total_delta=$((total_b - total_a))
idle_delta=$((idle_b - idle_a))
if (( total_delta > 0 )); then
  cpu_percent=$(awk -v total="$total_delta" -v idle="$idle_delta" 'BEGIN { printf "%.2f", (total-idle)*100/total }')
else
  cpu_percent=0
fi

memory_percent=$(awk '/MemTotal:/ { total=$2 } /MemAvailable:/ { available=$2 } END { if (total > 0) printf "%.2f", (total-available)*100/total; else print 0 }' /proc/meminfo)
disk_percent=$(df -P / | awk 'NR==2 { gsub("%", "", $5); print $5 }')
hostname_value=$(hostname)
platform_value=$(uname -sr)
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet nginx; then
  nginx_active=true
else
  nginx_active=false
fi

printf '{"cpu_percent":%s,"memory_percent":%s,"disk_percent":%s,"nginx_active":%s,"hostname":"%s","platform":"%s"}\n' \
  "$cpu_percent" "$memory_percent" "$disk_percent" "$nginx_active" \
  "$(printf '%s' "$hostname_value" | sed 's/\\/\\\\/g; s/"/\\"/g')" \
  "$(printf '%s' "$platform_value" | sed 's/\\/\\\\/g; s/"/\\"/g')"
