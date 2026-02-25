#!/bin/bash

# Generate a new PRD with auto-incremented ID and folder structure
# This script is portable — it resolves paths relative to the project root.

set -e

usage() {
    echo "Usage: $0 --name <feature-name>"
    echo ""
    echo "Creates a new PRD folder with auto-incremented ID and template."
    echo ""
    echo "Arguments:"
    echo "  --name    Feature name for the PRD (e.g., 'User Authentication') [required]"
    echo "  --help    Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --name 'User Authentication'"
    exit 1
}

# Resolve project root:
# 1. Explicit PROJECT_ROOT env var
# 2. Walk up from script location to find .git or project markers
# 3. Fall back to cwd
if [ -n "$PROJECT_ROOT" ]; then
    ROOT="$PROJECT_ROOT"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    candidate="$SCRIPT_DIR"
    ROOT=""
    while [ "$candidate" != "/" ]; do
        if [ -d "$candidate/.git" ] || [ -f "$candidate/pyproject.toml" ] || [ -f "$candidate/package.json" ]; then
            ROOT="$candidate"
            break
        fi
        candidate="$(dirname "$candidate")"
    done
    ROOT="${ROOT:-$(pwd)}"
fi

PRD_DIR="${ROOT}/prd"
mkdir -p "$PRD_DIR"

FEATURE_NAME=""

# Parse all flags
while [ $# -gt 0 ]; do
    case "$1" in
        --name)
            [ $# -lt 2 ] && usage
            FEATURE_NAME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: unknown argument '$1'"
            usage
            ;;
    esac
done

[ -z "$FEATURE_NAME" ] && { echo "Error: --name is required."; echo ""; usage; }
# Sanitize: lowercase, replace spaces with hyphens
FEATURE_SLUG=$(echo "$FEATURE_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')

# Find next ID by checking existing PRD folders
LAST_ID=$(ls -1d "$PRD_DIR"/prd-* 2>/dev/null | sed 's/.*prd-\([0-9]*\)-.*/\1/' | sort -n | tail -1)
if [ -z "$LAST_ID" ]; then
    NEXT_ID=1
else
    NEXT_ID=$((LAST_ID + 1))
fi

# Pad to 3 digits
PADDED_ID=$(printf "%03d" $NEXT_ID)

# Generate folder name and paths
FOLDER_NAME="prd-${PADDED_ID}-${FEATURE_SLUG}"
FOLDER_PATH="${PRD_DIR}/${FOLDER_NAME}"
PRD_FILE="${FOLDER_PATH}/prd.md"
TASKS_DIR="${FOLDER_PATH}/tasks"

# Create folder structure
mkdir -p "$TASKS_DIR"

# Create PRD from template
cat > "$PRD_FILE" << 'EOF'
# PRD PADDED_ID: FEATURE_TITLE

## Overview

_Brief description of the feature and why it's needed._

## Linked Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| - | - | - |

## Measures of Success

- [ ] _How do we know this is working?_
- [ ] _What metrics or outcomes indicate success?_

## Low Effort Version

_Minimal viable implementation. What's the simplest version that delivers value?_

## High Effort Version

_Full-featured implementation. What would the ideal solution look like?_

## Possible Future Extensions

- _What could this enable later?_
- _What are we explicitly deferring?_

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | DATE_TODAY | Initial draft |
EOF

# Create task placeholder
cat > "$TASKS_DIR/.gitkeep" << 'EOF'
# Tasks for this PRD go here
# Use: PROJECT_ROOT=. <skill-scripts>/new-task.sh "prd-XXX-name" "Task Name"
EOF

# Replace placeholders
sed -i '' "s/PADDED_ID/${PADDED_ID}/g" "$PRD_FILE"
sed -i '' "s/FEATURE_TITLE/${FEATURE_NAME}/g" "$PRD_FILE"
sed -i '' "s/DATE_TODAY/$(date +%Y-%m-%d)/g" "$PRD_FILE"

echo "Created: $FOLDER_PATH/"
echo "  - prd.md"
echo "  - tasks/"
