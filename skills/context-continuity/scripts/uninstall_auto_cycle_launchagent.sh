#!/usr/bin/env bash
set -euo pipefail

LABEL="com.leo.context-continuity-auto-cycle"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"

/bin/launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
/bin/rm -f "$PLIST_PATH"

echo "uninstalled_label: $LABEL"
echo "removed_plist: $PLIST_PATH"
