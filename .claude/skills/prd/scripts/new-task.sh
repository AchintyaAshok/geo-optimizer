#!/bin/bash

# Generate a new task within a PRD folder with enforced structure
# This script is portable — set PROJECT_ROOT or run from the project root.

set -e

usage() {
    echo "Usage: $0 --prd <prd-folder> --name <task-name>"
    echo ""
    echo "Creates a new task file within an existing PRD's tasks/ directory."
    echo ""
    echo "Arguments:"
    echo "  --prd     PRD folder name (e.g., prd-001-feature-name) [required]"
    echo "  --name    Task name (e.g., 'Set up project structure') [required]"
    echo "  --help    Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --prd prd-001-feature-name --name 'Set up project structure'"
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

PRD_FOLDER=""
TASK_NAME=""

# Parse all flags
while [ $# -gt 0 ]; do
    case "$1" in
        --prd)
            [ $# -lt 2 ] && usage
            PRD_FOLDER="$2"
            shift 2
            ;;
        --name)
            [ $# -lt 2 ] && usage
            TASK_NAME="$2"
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

[ -z "$PRD_FOLDER" ] && { echo "Error: --prd is required."; echo ""; usage; }
[ -z "$TASK_NAME" ] && { echo "Error: --name is required."; echo ""; usage; }

PRD_PATH="${PRD_DIR}/${PRD_FOLDER}"
TASKS_DIR="${PRD_PATH}/tasks"
PRD_FILE="${PRD_PATH}/prd.md"

if [ ! -d "$TASKS_DIR" ]; then
    echo "Error: Tasks directory not found: $TASKS_DIR"
    echo "Make sure the PRD folder exists."
    exit 1
fi

if [ ! -f "$PRD_FILE" ]; then
    echo "Error: PRD file not found: $PRD_FILE"
    exit 1
fi

# Extract PRD name from the prd.md file (first H1 heading)
PRD_NAME=$(grep -m1 "^# " "$PRD_FILE" | sed 's/^# //')

# Extract PRD ID from folder name (e.g., prd-001-name -> 001)
PRD_ID=$(echo "$PRD_FOLDER" | sed 's/prd-\([0-9]*\)-.*/\1/')

# Sanitize task name: lowercase, replace spaces with hyphens
TASK_SLUG=$(echo "$TASK_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')

# Find next task ID
LAST_ID=$(ls -1 "$TASKS_DIR"/*.md 2>/dev/null | grep -v ".gitkeep" | sed 's/.*\/\([0-9]*\)-.*/\1/' | sort -n | tail -1)
if [ -z "$LAST_ID" ]; then
    NEXT_ID=1
else
    NEXT_ID=$((LAST_ID + 1))
fi

# Pad to 3 digits
PADDED_ID=$(printf "%03d" $NEXT_ID)
TODAY=$(date +%Y-%m-%d)

# Generate filename
FILENAME="${PADDED_ID}-${TASK_SLUG}.md"
FILEPATH="${TASKS_DIR}/${FILENAME}"

# Create task from template with enforced structure
cat > "$FILEPATH" << EOF
---
parent_prd: ../${PRD_FOLDER}/prd.md
prd_name: "${PRD_NAME}"
prd_id: ${PRD_ID}
task_id: ${PADDED_ID}
created: ${TODAY}
state: pending
---

# Task ${PADDED_ID}: ${TASK_NAME}

## Metadata

| Field | Value |
|-------|-------|
| PRD | [${PRD_NAME}](../prd.md) |
| Created | ${TODAY} |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| ${TODAY} | Task created |

## Objective

_What this task accomplishes._

## Inputs

- _What's needed before starting_

## Outputs

- _What's produced when done_

## Steps

1. _Step one_
2. _Step two_

## Done Criteria

- [ ] _Criterion one_
- [ ] _Criterion two_

## Notes

_Any additional context or decisions made during execution._
EOF

echo "Created: $FILEPATH"
