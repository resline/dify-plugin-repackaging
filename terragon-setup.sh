#!/bin/bash
# =============================================================================
# Terragon Setup Script
# Master script that runs all Terragon setup components:
# - Chrome Headless Shell (for MCP Chrome DevTools)
# - Claude Code Superpowers and Anthropic Skills
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

echo ">>> Running Chrome Headless Shell setup..."
echo ""
"$SCRIPT_DIR/terragon-scripts/terragon-chrome-setup.sh"
echo ""

# =============================================================================
# Skills & Superpowers Setup
# =============================================================================

echo ">>> Running Skills & Superpowers setup..."
echo ""
"$SCRIPT_DIR/terragon-scripts/terragon-skills-setup.sh"
echo ""

# =============================================================================
# Summary
# =============================================================================

echo "======================================"
echo "  Terragon Setup Complete!"
echo "======================================"
echo ""
echo "Components installed:"
echo "  ✓ Chrome Headless Shell (port 9222)"
echo "  ✓ Claude Code Superpowers"
echo "  ✓ Anthropic Skills"
echo ""
echo "You can now use MCP Chrome DevTools and enhanced Claude capabilities."
