#!/bin/bash
# Build the mod and open it in ares: ./run-ares.sh [build.sh options]
set -o pipefail
cd "$(dirname "$0")"
ROM=$(./build.sh "$@" | tail -1) || exit 1
osascript -e 'tell application "ares" to quit' 2>/dev/null
sleep 0.4
open -a /Applications/ares.app --args "$PWD/$ROM"
