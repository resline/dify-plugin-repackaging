# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Dify plugin repackaging tool that downloads and repackages Dify plugins with their Python dependencies for offline installation. It supports three sources:
1. Dify Marketplace
2. GitHub releases
3. Local .difypkg files

## Common Commands

### Docker Usage
```bash
# Build Docker image
docker build -t dify-plugin-repackaging .

# Run with default parameters (Linux)
docker run -v $(pwd):/app dify-plugin-repackaging

# Run with custom parameters (Linux)
docker run -v $(pwd):/app dify-plugin-repackaging ./plugin_repackaging.sh -p manylinux_2_17_x86_64 market antv visualization 0.1.7

# Windows equivalent
docker run -v %cd%:/app dify-plugin-repackaging
```

### Direct Script Usage
```bash
# From Dify Marketplace
./plugin_repackaging.sh market [plugin_author] [plugin_name] [plugin_version]
./plugin_repackaging.sh market langgenius agent 0.0.9

# From GitHub releases
./plugin_repackaging.sh github [repo] [release_title] [assets_name.difypkg]
./plugin_repackaging.sh github junjiem/dify-plugin-tools-dbquery v0.0.2 db_query.difypkg

# From local package
./plugin_repackaging.sh local [difypkg_path]
./plugin_repackaging.sh local ./db_query.difypkg

# Cross-platform repackaging
./plugin_repackaging.sh -p manylinux2014_x86_64 market antv visualization 0.1.7
./plugin_repackaging.sh -p manylinux2014_aarch64 -s linux-arm64 local ./plugin.difypkg
```

## Architecture Overview

### Core Components

1. **plugin_repackaging.sh** - Main shell script that orchestrates the repackaging process
   - Handles three download sources (market, github, local)
   - Manages platform-specific packaging with `-p` option
   - Uses platform-specific dify-plugin binaries for final packaging

2. **Platform-specific binaries** - Pre-compiled dify-plugin tools
   - `dify-plugin-darwin-amd64-5g` - macOS x86_64
   - `dify-plugin-darwin-arm64-5g` - macOS ARM64
   - `dify-plugin-linux-amd64-5g` - Linux x86_64
   - `dify-plugin-linux-arm64-5g` - Linux ARM64

3. **Dockerfile** - Containerized environment for consistent repackaging
   - Based on Python 3.12-slim
   - Includes Chinese mirrors for faster downloads in China
   - Pre-configured with example command

### Repackaging Process

1. **Download Phase**: Fetches the original .difypkg from specified source
2. **Extraction**: Unzips the package to a temporary directory
3. **Dependency Resolution**: Downloads all Python dependencies from PyPI (or configured mirror)
4. **Offline Packaging**: 
   - Modifies requirements.txt to use local wheels
   - Updates .difyignore/.gitignore to exclude wheels directory
   - Repackages with dify-plugin tool including all dependencies

### Key Environment Variables

- `GITHUB_API_URL` - Default: https://github.com
- `MARKETPLACE_API_URL` - Default: https://marketplace.dify.ai
- `PIP_MIRROR_URL` - Default: https://mirrors.aliyun.com/pypi/simple

### Platform Considerations

- Script auto-detects OS (Linux/Darwin) and architecture (x86_64/arm64)
- Cross-platform packaging supported via `-p` option with pip platform strings
- Common platforms: `manylinux2014_x86_64`, `manylinux2014_aarch64`
- Note: `unzip` installation uses `yum`, suitable for RPM-based Linux systems

## Development Notes

- Python version should match dify-plugin-daemon (currently 3.12.x)
- Output packages are named with `-offline` suffix by default
- Custom suffix can be specified with `-s` option
- All downloaded dependencies are stored in `./wheels` directory within the package