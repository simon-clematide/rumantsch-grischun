#!/usr/bin/env bash
#
# scripts/deploy_to_space.sh
# Synchronizes build artifacts, requirements, and app.py to the dedicated Hugging Face Space repository.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SPACE_DIR="${ROOT_DIR}/spaces/romansh-morphology"

echo "=========================================================="
echo "  Deploying Rumantsch Morphology to Hugging Face Space"
echo "=========================================================="

# 1. Check Space repository presence
if [ ! -d "${SPACE_DIR}/.git" ]; then
    echo "Space repository not found at ${SPACE_DIR}."
    echo "Cloning target repository..."
    mkdir -p "${ROOT_DIR}/spaces"
    git clone https://huggingface.co/spaces/simon-clmtd/romansh-morphology "${SPACE_DIR}"
fi

# 2. Verify source FST binaries exist
if [ ! -f "${ROOT_DIR}/GrischunGuessing.fst" ]; then
    echo "Error: GrischunGuessing.fst not found in repository root!"
    echo "Please build with: make -f Makefile-foma"
    exit 1
fi

if [ ! -f "${ROOT_DIR}/fstbinaries/generator.fst" ]; then
    echo "Error: fstbinaries/generator.fst not found!"
    echo "Please build with: make -f Makefile-foma"
    exit 1
fi

# 3. Synchronize deployment files
echo "Syncing deployment assets to ${SPACE_DIR}..."
mkdir -p "${SPACE_DIR}/fstbinaries" "${SPACE_DIR}/data"

cp -v "${ROOT_DIR}/GrischunGuessing.fst" "${SPACE_DIR}/"
cp -v "${ROOT_DIR}/fstbinaries/generator.fst" "${SPACE_DIR}/fstbinaries/"
cp -v "${ROOT_DIR}/data/model.mod" "${SPACE_DIR}/data/model.mod"
cp -v "${ROOT_DIR}/wapiti_src.tar.gz" "${SPACE_DIR}/"
cp -v "${ROOT_DIR}/app.py" "${SPACE_DIR}/app.py"
cp -v "${ROOT_DIR}/requirements.txt" "${SPACE_DIR}/requirements.txt"
cp -v "${ROOT_DIR}/packages.txt" "${SPACE_DIR}/packages.txt"

# 4. Git status & commit in Space directory
cd "${SPACE_DIR}"

if git diff --quiet && git diff --staged --quiet && [ -z "$(git status --porcelain)" ]; then
    echo "No changes detected in Space repository."
else
    echo "Changes detected. Staging and committing..."
    git add .
    COMMIT_MSG="Deploy update: $(date '+%Y-%m-%d %H:%M:%S')"
    if [ $# -gt 0 ]; then
        COMMIT_MSG="$*"
    fi
    git commit -m "${COMMIT_MSG}"
    echo "Committed: ${COMMIT_MSG}"
fi

# 5. Push instructions
echo "----------------------------------------------------------"
echo "To push to Hugging Face, run:"
echo "  cd ${SPACE_DIR}"
echo "  git push origin main"
echo "----------------------------------------------------------"

if [ "${1:-}" = "--push" ] || [ "${2:-}" = "--push" ]; then
    echo "Attempting git push..."
    git push origin main
fi

echo "Done."
