#!/bin/bash
# =============================================================================
# Terragon Setup Script
# Master script that runs all Terragon setup components:
# - Chrome Headless Shell (for Playwright-based webapp testing)
# - Claude Code Skills verification
# Run this after each clean workspace initialization
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "  Terragon Full Setup"
echo "======================================"
echo ""

# =============================================================================
# Chrome Headless Shell Setup
# =============================================================================

echo ">>> Setting up Chrome Headless Shell..."
echo ""

if command -v npx &> /dev/null; then
  npx playwright install chromium-headless-shell
  echo ""
  echo "  Chrome Headless Shell installed via Playwright."
else
  echo "  WARNING: npx not found. Skipping Chrome Headless Shell installation."
  echo "  Install Node.js and run this script again to enable browser automation."
fi

echo ""

# =============================================================================
# Skills Verification
# =============================================================================

echo ">>> Verifying Claude Code Skills..."
echo ""

SKILLS_DIR="$SCRIPT_DIR/.claude/skills"
if [ -d "$SKILLS_DIR" ]; then
  SKILL_COUNT=$(ls -1d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l)
  echo "  Found $SKILL_COUNT skills in $SKILLS_DIR"
else
  echo "  WARNING: Skills directory not found at $SKILLS_DIR"
  echo "  Skills may need to be synced manually."
fi

echo ""

# =============================================================================
# Summary
# =============================================================================

echo "======================================"
echo "  Terragon Setup Complete!"
echo "======================================"
echo ""
echo "Components installed:"
echo "  - Chrome Headless Shell (Playwright)"
echo "  - Claude Code Skills"
echo ""
echo "You can now use Playwright-based webapp testing and enhanced Claude capabilities."
