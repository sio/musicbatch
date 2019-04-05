#!/usr/bin/env bash
#
# Prepare wav samples for ABX testing
#

set -e

TRANSCODING_PARAMETERS="-f opus -acodec libopus -b:a 96 -vbr on"
INPUT="$1"
DEST_DIR="./abx-samples"

SAMPLE_A="$DEST_DIR/original.wav"
SAMPLE_B="$DEST_DIR/transcoded.wav"
TEMPFILE="$DEST_DIR/tempfile"

mkdir "$DEST_DIR" || true
ffmpeg -i "$INPUT" "$SAMPLE_A"
ffmpeg -i "$SAMPLE_A" $TRANSCODING_PARAMETERS "$TEMPFILE"
ffmpeg -i "$TEMPFILE" "$SAMPLE_B"
rm "$TEMPFILE"
