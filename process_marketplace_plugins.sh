#!/bin/bash
# Process all .difypkg files from plugin_from_marketplace directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE_DIR="${SCRIPT_DIR}/plugin_from_marketplace"
OUTPUT_DIR="${SCRIPT_DIR}/repackaged_plugins"
LOG_FILE="${SCRIPT_DIR}/process_marketplace_plugins.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize log
echo "Processing started at $(date)" > "${LOG_FILE}"

# Check if marketplace directory exists
if [ ! -d "${MARKETPLACE_DIR}" ]; then
    echo -e "${RED}Error: Directory '${MARKETPLACE_DIR}' does not exist${NC}"
    echo "Error: Directory '${MARKETPLACE_DIR}' does not exist" >> "${LOG_FILE}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Count total files to process
TOTAL_FILES=$(find "${MARKETPLACE_DIR}" -name "*.difypkg" -type f | wc -l)

if [ ${TOTAL_FILES} -eq 0 ]; then
    echo -e "${YELLOW}No .difypkg files found in ${MARKETPLACE_DIR}${NC}"
    echo "No .difypkg files found in ${MARKETPLACE_DIR}" >> "${LOG_FILE}"
    exit 0
fi

echo -e "${GREEN}Found ${TOTAL_FILES} plugin(s) to process${NC}"
echo "Found ${TOTAL_FILES} plugin(s) to process" >> "${LOG_FILE}"

# Process each .difypkg file
PROCESSED=0
FAILED=0

# Default platform - can be overridden by command line argument
PLATFORM="${1:-manylinux2014_x86_64}"
SUFFIX="${2:-offline}"

echo -e "${GREEN}Using platform: ${PLATFORM}${NC}"
echo -e "${GREEN}Using suffix: ${SUFFIX}${NC}"
echo "Platform: ${PLATFORM}, Suffix: ${SUFFIX}" >> "${LOG_FILE}"

# Process each file
find "${MARKETPLACE_DIR}" -name "*.difypkg" -type f | while read -r plugin_file; do
    FILENAME=$(basename "${plugin_file}")
    echo -e "\n${YELLOW}Processing: ${FILENAME}${NC}"
    echo -e "\nProcessing: ${FILENAME}" >> "${LOG_FILE}"
    
    # Run the repackaging script
    if [ -n "${PLATFORM}" ]; then
        "${SCRIPT_DIR}/plugin_repackaging.sh" -p "${PLATFORM}" -s "${SUFFIX}" local "${plugin_file}" >> "${LOG_FILE}" 2>&1
    else
        "${SCRIPT_DIR}/plugin_repackaging.sh" -s "${SUFFIX}" local "${plugin_file}" >> "${LOG_FILE}" 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        PROCESSED=$((PROCESSED + 1))
        echo -e "${GREEN}✓ Successfully processed: ${FILENAME}${NC}"
        echo "✓ Successfully processed: ${FILENAME}" >> "${LOG_FILE}"
        
        # Move repackaged file to output directory
        REPACKAGED_FILE="${FILENAME%.difypkg}-${SUFFIX}.difypkg"
        if [ -f "${SCRIPT_DIR}/${REPACKAGED_FILE}" ]; then
            mv "${SCRIPT_DIR}/${REPACKAGED_FILE}" "${OUTPUT_DIR}/"
            echo "  Moved to: ${OUTPUT_DIR}/${REPACKAGED_FILE}" >> "${LOG_FILE}"
        fi
        
        # Clean up temporary directory
        TEMP_DIR="${SCRIPT_DIR}/${FILENAME%.difypkg}"
        if [ -d "${TEMP_DIR}" ]; then
            rm -rf "${TEMP_DIR}"
            echo "  Cleaned up temporary directory: ${TEMP_DIR}" >> "${LOG_FILE}"
        fi
    else
        FAILED=$((FAILED + 1))
        echo -e "${RED}✗ Failed to process: ${FILENAME}${NC}"
        echo "✗ Failed to process: ${FILENAME}" >> "${LOG_FILE}"
    fi
done

# Summary
echo -e "\n${GREEN}=== Processing Complete ===${NC}"
echo -e "${GREEN}Total files: ${TOTAL_FILES}${NC}"
echo -e "${GREEN}Successfully processed: ${PROCESSED}${NC}"
if [ ${FAILED} -gt 0 ]; then
    echo -e "${RED}Failed: ${FAILED}${NC}"
fi
echo -e "${GREEN}Output directory: ${OUTPUT_DIR}${NC}"
echo -e "${GREEN}Log file: ${LOG_FILE}${NC}"

echo -e "\n=== Processing Complete ===" >> "${LOG_FILE}"
echo "Total files: ${TOTAL_FILES}" >> "${LOG_FILE}"
echo "Successfully processed: ${PROCESSED}" >> "${LOG_FILE}"
echo "Failed: ${FAILED}" >> "${LOG_FILE}"
echo "Processing ended at $(date)" >> "${LOG_FILE}"