#!/usr/bin/env bash
# download_wide_field_index.sh
#
# Downloads the Astrometry.net "wide field" index files needed to
# plate-solve very wide fields — e.g. the ZWO Seestar S30 Pro's wide
# camera (63 deg FOV) in "Median (Milky Way Mode)" stacking.
#
# Astrometry.net's rule of thumb: grab index files whose skymark
# ("quad") size is 10%-100% of your field width. For a 63 deg field
# that's roughly 6-63 deg, which corresponds to index files 4116-4119
# (the widest available in the standard 4100-series — there is no
# larger pre-built index than 4119). These files are tiny (a few
# hundred KB total), since wide-scale indexes need far fewer skymarks
# than fine ones.
#
# Usage:
#   ./download_wide_field_index.sh [destination_dir]
#
# If destination_dir is omitted, the script auto-detects Homebrew's
# astrometry.net data directory (Apple Silicon or Intel) and falls
# back to /usr/local/astrometry/data if neither is found.

set -euo pipefail

INDEXES=(4116 4117 4118 4119)
BASE_URL="http://data.astrometry.net/4100"

# ---- pick a destination directory -----------------------------------------
if [ "${1:-}" != "" ]; then
    DEST="$1"
elif command -v brew >/dev/null 2>&1 && brew --prefix astrometry-net >/dev/null 2>&1; then
    DEST="$(brew --prefix astrometry-net)/share/astrometry/data"
elif [ -d /opt/homebrew/share/astrometry/data ]; then
    DEST="/opt/homebrew/share/astrometry/data"
elif [ -d /usr/local/share/astrometry/data ]; then
    DEST="/usr/local/share/astrometry/data"
else
    DEST="/usr/local/astrometry/data"
fi

echo "Destination: $DEST"
mkdir -p "$DEST"

# ---- fetch official checksums for verification -----------------------------
TMP_MD5="$(mktemp)"
trap 'rm -f "$TMP_MD5"' EXIT
curl -fsSL "$BASE_URL/md5sums.txt" -o "$TMP_MD5"

# ---- download each index file (resumable, skips if already present/valid) --
for idx in "${INDEXES[@]}"; do
    fname="index-${idx}.fits"
    dest_path="$DEST/$fname"
    url="$BASE_URL/$fname"

    if [ -f "$dest_path" ]; then
        expected="$(grep " $fname\$" "$TMP_MD5" | awk '{print $1}' || true)"
        actual="$(md5 -q "$dest_path" 2>/dev/null || md5sum "$dest_path" 2>/dev/null | awk '{print $1}')"
        if [ -n "$expected" ] && [ "$expected" == "$actual" ]; then
            echo "OK (already present, checksum verified): $fname"
            continue
        fi
    fi

    echo "Downloading $fname ..."
    curl -fL --retry 3 -C - -o "$dest_path" "$url"

    expected="$(grep " $fname\$" "$TMP_MD5" | awk '{print $1}' || true)"
    actual="$(md5 -q "$dest_path" 2>/dev/null || md5sum "$dest_path" 2>/dev/null | awk '{print $1}')"
    if [ -n "$expected" ] && [ "$expected" != "$actual" ]; then
        echo "WARNING: checksum mismatch for $fname (expected $expected, got $actual)" >&2
    else
        echo "OK: $fname"
    fi
done

echo
echo "Done. Wide-field index files are in: $DEST"
echo "In Siril, make sure Preferences -> Astrometry -> solve-field path is set,"
echo "and that this data directory is where astrometry.cfg (or the solve-field"
echo "install) expects index files -- usually the same 'data' directory next to"
echo "astrometry.cfg (e.g. \$(brew --prefix astrometry-net)/etc/astrometry.cfg)."
