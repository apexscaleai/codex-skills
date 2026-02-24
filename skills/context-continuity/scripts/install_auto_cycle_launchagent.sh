#!/usr/bin/env bash
set -euo pipefail

LABEL="com.leo.context-continuity-auto-cycle"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/${LABEL}.plist"
SCRIPT_PATH="$HOME/.codex/skills/context-continuity/scripts/start_auto_cycle.sh"
LOG_OUT="$HOME/.codex/log/context-continuity-auto-cycle.out.log"
LOG_ERR="$HOME/.codex/log/context-continuity-auto-cycle.err.log"

mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$HOME/.codex/log"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${SCRIPT_PATH}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${LOG_OUT}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_ERR}</string>

    <key>EnvironmentVariables</key>
    <dict>
      <key>CODEX_HOME</key>
      <string>${HOME}/.codex</string>
      <key>CONTEXT_CONTINUITY_REPO</key>
      <string>/Users/leo</string>
      <key>CONTEXT_CONTINUITY_BUDGET</key>
      <string>1000</string>
      <key>CONTEXT_CONTINUITY_INTERVAL_SECONDS</key>
      <string>120</string>
      <key>CONTEXT_CONTINUITY_SNAPSHOT_MIN_SECONDS</key>
      <string>1800</string>
      <key>CONTEXT_CONTINUITY_QUERY</key>
      <string></string>
      <key>CONTEXT_CONTINUITY_TASK</key>
      <string></string>
    </dict>
  </dict>
</plist>
PLIST

/bin/chmod 644 "$PLIST_PATH"
/bin/chmod +x "$SCRIPT_PATH"

/bin/launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
/bin/launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
/bin/launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "installed_plist: $PLIST_PATH"
echo "label: $LABEL"
echo "stdout_log: $LOG_OUT"
echo "stderr_log: $LOG_ERR"
/bin/launchctl print "gui/$(id -u)/${LABEL}" | /usr/bin/head -n 40
