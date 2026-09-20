#!/usr/bin/env bash
# memwatch.sh -- sample WoW Forever client memory/GPU over time (leak detection). Linux only.
# Usage: memwatch.sh [interval_seconds]   (default 30)
# Output: CSV appended to memwatch.csv next to this script. One row per sample.
#   ts, pid, uptime_s, rss_mb, anon_mb, file_mb, swap_mb, threads, vram_mb, gtt_mb, sys_avail_mb, proc_vram_mb, gpu_busy_pct, gpu_sclk_mhz, gpu_mclk_mhz, gpu_power_w
#   vram_mb = card-wide; proc_vram_mb = VRAM held by the WoW process itself (DRM fdinfo)
# Attribution guide:
#   rss/anon climbing, vram flat      -> client heap (engine or Lua). Compare in-game
#                                        /run UpdateAddOnMemoryUsage(); print(collectgarbage("count")/1024)
#   vram/gtt climbing, rss flat       -> GPU: vkd3d-proton / RADV / texture streaming
#   both flat, but stutter grows      -> not memory; look at shader cache or CPU
set -u
INTERVAL="${1:-30}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/memwatch.csv"
# Machine-specific paths live in ../forever.env (gitignored), see forever.env.example
if [ -f "$HERE/../forever.env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue;; esac
    case "$line" in *=*) ;; *) continue;; esac
    k="${line%%=*}"; v="${line#*=}"; v="${v%\"}"; v="${v#\"}"; v="${v/#\~/$HOME}"
    [ -z "${!k:-}" ] && export "$k=$v"
  done < "$HERE/../forever.env"
fi
BETA="${FOREVER_BETA_DIR:-$HOME/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_classic_beta_}"
GXLOG="$BETA/Logs/gx.log"
GXDIR="$HERE/gxlogs"   # gx.log is overwritten per session; archived here when the client exits
LASTPID=""
CARD=""
for d in /sys/class/drm/card*/device; do
  if [ -f "$d/mem_info_vram_total" ] && [ "$(cat "$d/mem_info_vram_total")" -gt 4294967296 ]; then CARD="$d"; break; fi
done
[ -s "$OUT" ] || echo "ts,pid,uptime_s,rss_mb,anon_mb,file_mb,swap_mb,threads,vram_mb,gtt_mb,sys_avail_mb,proc_vram_mb,gpu_busy_pct,gpu_sclk_mhz,gpu_mclk_mhz,gpu_power_w" >> "$OUT"
while :; do
  PID=$(pgrep -x WowB.exe | while read -r p; do [ -r "/proc/$p/status" ] && ! grep -q 'State:.*Z' "/proc/$p/status" && echo "$p" && break; done)
  if [ -n "${PID:-}" ] && [ -r "/proc/$PID/smaps_rollup" ]; then
    UP=$(( $(cut -d. -f1 /proc/uptime) - $(awk '{print int($22/100)}' /proc/$PID/stat) ))
    read -r RSS ANON FILE SWAP <<< "$(awk '/^Rss:/{r=$2} /^Anonymous:/{a=$2} /^Shared_Clean:|^Private_Clean:/{f+=$2} /^Swap:/{s=$2} END{printf "%d %d %d %d", r/1024, a/1024, f/1024, s/1024}' /proc/$PID/smaps_rollup)"
    THR=$(awk '/^Threads:/{print $2}' /proc/$PID/status)
    PVRAM=$(cat /proc/$PID/fdinfo/* 2>/dev/null | awk '/^drm-client-id/{c=$2} /^drm-memory-vram/{if(!s[c]++){t+=$2}} END{printf "%d", t/1024}')
  else
    PID=""; UP=""; RSS=""; ANON=""; FILE=""; SWAP=""; THR=""; PVRAM=""
  fi
  if [ -n "$LASTPID" ] && [ -z "$PID" ] && [ -f "$GXLOG" ]; then
    mkdir -p "$GXDIR"; cp "$GXLOG" "$GXDIR/gx-$(date +%Y%m%d-%H%M%S)-pid$LASTPID.log"
  fi
  LASTPID="$PID"
  if [ -n "$CARD" ]; then
    VRAM=$(( $(cat "$CARD/mem_info_vram_used") / 1048576 )); GTT=$(( $(cat "$CARD/mem_info_gtt_used") / 1048576 ))
  else
    VRAM=""; GTT=""
  fi
  AVAIL=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
  GBUSY=""; SCLK=""; MCLK=""; GPW=""
  if [ -n "$CARD" ]; then
    GBUSY=$(cat "$CARD/gpu_busy_percent" 2>/dev/null)
    SCLK=$(grep '\*' "$CARD/pp_dpm_sclk" 2>/dev/null | head -1 | grep -oE '[0-9]+Mhz' | tr -d 'Mhz')
    MCLK=$(grep '\*' "$CARD/pp_dpm_mclk" 2>/dev/null | head -1 | grep -oE '[0-9]+Mhz' | tr -d 'Mhz')
    HW=$(ls -d "$CARD"/hwmon/hwmon* 2>/dev/null | head -1)
    [ -n "$HW" ] && [ -f "$HW/power1_average" ] && GPW=$(( $(cat "$HW/power1_average") / 1000000 ))
    [ -z "$GPW" ] && [ -n "$HW" ] && [ -f "$HW/power1_input" ] && GPW=$(( $(cat "$HW/power1_input") / 1000000 ))
  fi
  echo "$(date +%FT%T),$PID,$UP,$RSS,$ANON,$FILE,$SWAP,$THR,$VRAM,$GTT,$AVAIL,$PVRAM,$GBUSY,$SCLK,$MCLK,$GPW" >> "$OUT"
  sleep "$INTERVAL"
done
