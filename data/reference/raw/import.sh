#!/bin/sh
# Import the master pipeline ODS from the author's working copy.
#
# This directory holds read-only snapshots of files maintained elsewhere.
# Corrections are made in the master, then re-imported here (see README.md).
#
# SNAPSHOT POLICY (ticket 0430): snapshots are datestamped immutable captures.
# The script writes pipeline-YYYY-MM-DD.ods (today's date) and refuses to
# overwrite a snapshot already known to git.
#
# The master lives on the author's machine only — it is absent from CI and
# from the workstation. This script is documentation-grade: it records where
# the master lives and how the snapshot is refreshed. It is never run in CI.
#
# Override SRC_ODS if the master lives elsewhere:
#   SRC_ODS=/path/to/pipeline.ods ./import.sh
set -eu
SRC_ODS="${SRC_ODS:-$HOME/CNRS/papiers/actif/Market report on Gas to Power/pipeline.ods}"
DEST_DIR="$(dirname "$0")"
CAPTURE_DATE="$(date +%F)"
DEST="$DEST_DIR/pipeline-$CAPTURE_DATE.ods"

if [ ! -f "$SRC_ODS" ]; then
    echo "Master ODS not found: $SRC_ODS" >&2
    echo "Set SRC_ODS to the master's location, or run this on the author's machine." >&2
    exit 1
fi

# Refuse to overwrite a snapshot already committed to git
if git ls-files --error-unmatch "$DEST" >/dev/null 2>&1; then
    echo "Snapshot already exists in git: $DEST" >&2
    echo "A same-day re-import before the first commit may overwrite; a committed snapshot never." >&2
    exit 1
fi

cp "$SRC_ODS" "$DEST"
echo "Imported $SRC_ODS -> $DEST (capture date: $CAPTURE_DATE)"
