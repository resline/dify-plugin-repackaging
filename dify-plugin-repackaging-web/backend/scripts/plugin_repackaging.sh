#!/bin/bash
# author: Junjie.M
set -euo pipefail

# SEC-025: Cleanup temporary files on failure
CLEANUP_DIR=""
cleanup() {
	if [[ -n "$CLEANUP_DIR" && -d "$CLEANUP_DIR" ]]; then
		echo "Cleaning up temporary directory: ${CLEANUP_DIR}"
		rm -rf "$CLEANUP_DIR"
	fi
}
trap cleanup EXIT

DEFAULT_GITHUB_API_URL=https://github.com
DEFAULT_MARKETPLACE_API_URL=https://marketplace.dify.ai
DEFAULT_PIP_MIRROR_URL=https://mirrors.aliyun.com/pypi/simple

GITHUB_API_URL="${GITHUB_API_URL:-$DEFAULT_GITHUB_API_URL}"
MARKETPLACE_API_URL="${MARKETPLACE_API_URL:-$DEFAULT_MARKETPLACE_API_URL}"
PIP_MIRROR_URL="${PIP_MIRROR_URL:-$DEFAULT_PIP_MIRROR_URL}"

CURR_DIR=$(dirname "$0")
cd "$CURR_DIR"
CURR_DIR=$(pwd)
USER=$(whoami)
ARCH_NAME=$(uname -m)
OS_TYPE=$(uname)
OS_TYPE=$(echo "$OS_TYPE" | tr '[:upper:]' '[:lower:]')

CMD_NAME="dify-plugin-${OS_TYPE}-amd64-5g"
if [[ "arm64" == "$ARCH_NAME" || "aarch64" == "$ARCH_NAME" ]]; then
	CMD_NAME="dify-plugin-${OS_TYPE}-arm64-5g"
fi

PIP_PLATFORM=""
PACKAGE_SUFFIX="offline"

market(){
	if [[ -z "$2" || -z "$3" || -z "$4" ]]; then
		echo ""
		echo "Usage: "$0" market [plugin author] [plugin name] [plugin version]"
		echo "Example:"
		echo "	"$0" market junjiem mcp_sse 0.0.1"
		echo "	"$0" market langgenius agent 0.0.9"
		echo ""
		exit 1
	fi
	echo "From the Dify Marketplace downloading ..."
	PLUGIN_AUTHOR="$2"
	PLUGIN_NAME="$3"
	PLUGIN_VERSION="$4"
	PLUGIN_PACKAGE_PATH="${CURR_DIR}/${PLUGIN_AUTHOR}-${PLUGIN_NAME}_${PLUGIN_VERSION}.difypkg"
	PLUGIN_DOWNLOAD_URL="${MARKETPLACE_API_URL}/api/v1/plugins/${PLUGIN_AUTHOR}/${PLUGIN_NAME}/${PLUGIN_VERSION}/download"
	echo "Downloading ${PLUGIN_DOWNLOAD_URL} ..."
	curl -L -o "${PLUGIN_PACKAGE_PATH}" "${PLUGIN_DOWNLOAD_URL}"
	if [[ $? -ne 0 ]]; then
		echo "Download failed, please check the plugin author, name and version."
		exit 1
	fi
	echo "Download success."
	repackage "${PLUGIN_PACKAGE_PATH}"
}

github(){
	if [[ -z "$2" || -z "$3" || -z "$4" ]]; then
		echo ""
		echo "Usage: "$0" github [Github repo] [Release title] [Assets name (include .difypkg suffix)]"
		echo "Example:"
		echo "	"$0" github junjiem/dify-plugin-tools-dbquery v0.0.2 db_query.difypkg"
		echo "	"$0" github https://github.com/junjiem/dify-plugin-agent-mcp_sse 0.0.1 agent-mcp_see.difypkg"
		echo ""
		exit 1
	fi
	echo "From the Github downloading ..."
	GITHUB_REPO="$2"
	if [[ "${GITHUB_REPO}" != "${GITHUB_API_URL}"* ]]; then
		GITHUB_REPO="${GITHUB_API_URL}/${GITHUB_REPO}"
	fi
	RELEASE_TITLE="$3"
	ASSETS_NAME="$4"
	PLUGIN_NAME="${ASSETS_NAME%.difypkg}"
	PLUGIN_PACKAGE_PATH="${CURR_DIR}/${PLUGIN_NAME}-${RELEASE_TITLE}.difypkg"
	PLUGIN_DOWNLOAD_URL="${GITHUB_REPO}/releases/download/${RELEASE_TITLE}/${ASSETS_NAME}"
	echo "Downloading ${PLUGIN_DOWNLOAD_URL} ..."
	curl -L -o "${PLUGIN_PACKAGE_PATH}" "${PLUGIN_DOWNLOAD_URL}"
	if [[ $? -ne 0 ]]; then
		echo "Download failed, please check the github repo, release title and assets name."
		exit 1
	fi
	echo "Download success."
	repackage "${PLUGIN_PACKAGE_PATH}"
}

_local(){
	echo "$2"
	if [[ -z "$2" ]]; then
		echo ""
		echo "Usage: "$0" local [difypkg path]"
		echo "Example:"
		echo "	"$0" local ./db_query.difypkg"
		echo "	"$0" local /root/dify-plugin/db_query.difypkg"
		echo ""
		exit 1
	fi
	# Validate path doesn't contain shell metacharacters
	if [[ "$2" =~ [\;\|\&\$\`] ]]; then
		echo "Error: Invalid path. Path contains shell metacharacters."
		exit 1
	fi
	PLUGIN_PACKAGE_PATH="$(realpath "$2")"
	repackage "${PLUGIN_PACKAGE_PATH}"
}

repackage(){
	local PACKAGE_PATH="$1"
	PACKAGE_NAME_WITH_EXTENSION=$(basename "${PACKAGE_PATH}")
	PACKAGE_NAME="${PACKAGE_NAME_WITH_EXTENSION%.*}"
	# SEC-025: Register extraction directory for cleanup on failure
	CLEANUP_DIR="${CURR_DIR}/${PACKAGE_NAME}"
	echo "Unziping ..."
	install_unzip

	# SEC-002: Validate ZIP entries for path traversal (Zip Slip protection)
	if zipinfo -1 "${PACKAGE_PATH}" | grep -qE '(^|/)\.\.(/|$)'; then
		echo "Error: Archive contains path traversal entries. Aborting."
		exit 1
	fi
	# SEC-015: Check uncompressed size to prevent zip bombs (max 500MB)
	local UNCOMPRESSED_SIZE
	UNCOMPRESSED_SIZE=$(zipinfo -t "${PACKAGE_PATH}" 2>/dev/null | grep -oP '\d+(?= bytes)' | tail -1)
	if [[ -n "$UNCOMPRESSED_SIZE" ]] && [[ "$UNCOMPRESSED_SIZE" -gt 524288000 ]]; then
		echo "Error: Archive uncompressed size exceeds 500MB limit. Aborting."
		exit 1
	fi

	unzip -o "${PACKAGE_PATH}" -d "${CURR_DIR}/${PACKAGE_NAME}"
	if [[ $? -ne 0 ]]; then
		echo "Unzip failed."
		exit 1
	fi
	echo "Unzip success."
	echo "Repackaging ..."
	cd "${CURR_DIR}/${PACKAGE_NAME}"

	# SEC-009: Sanitize requirements.txt - remove dangerous pip directives
	if [ -f requirements.txt ]; then
		# Remove lines with pip options, VCS URLs, direct URLs, and editable installs
		sed -i '/^[[:space:]]*--/d; /^[[:space:]]*-[efic]/d; /git+/d; /svn+/d; /hg+/d; /bzr+/d; /https\?:\/\//d; /ftp:\/\//d; /@[[:space:]]*http/d' requirements.txt
	fi

	# SEC-001: Always use --only-binary=:all: to prevent setup.py execution
	# SEC-008: Removed --trusted-host to enforce SSL verification
	pip download --only-binary=:all: ${PIP_PLATFORM} -r requirements.txt -d ./wheels --index-url "${PIP_MIRROR_URL}"
	if [[ $? -ne 0 ]]; then
		echo "Pip download failed."
		exit 1
	fi
	if [[ "linux" == "$OS_TYPE" ]]; then
		sed -i '1i\--no-index --find-links=./wheels/' requirements.txt
	elif [[ "darwin" == "$OS_TYPE" ]]; then
		sed -i ".bak" '1i\
--no-index --find-links=./wheels/
	  ' requirements.txt
		rm -f requirements.txt.bak
	fi
	IGNORE_PATH=.difyignore
	if [ ! -f "$IGNORE_PATH" ]; then
		IGNORE_PATH=.gitignore
	fi
	if [ -f "$IGNORE_PATH" ]; then
		if [[ "linux" == "$OS_TYPE" ]]; then
			sed -i '/^wheels\//d' "${IGNORE_PATH}"
		elif [[ "darwin" == "$OS_TYPE" ]]; then
			sed -i ".bak" '/^wheels\//d' "${IGNORE_PATH}"
			rm -f "${IGNORE_PATH}.bak"
		fi
	fi
	cd "${CURR_DIR}"
	chmod 755 "${CURR_DIR}/${CMD_NAME}"
	if ! "${CURR_DIR}/${CMD_NAME}" plugin package "${CURR_DIR}/${PACKAGE_NAME}" -o "${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg"; then
		echo "Error: Repackaging failed"
		exit 1
	fi
	# Verify output file exists
	if [ ! -f "${CURR_DIR}/${PACKAGE_NAME}-${PACKAGE_SUFFIX}.difypkg" ]; then
		echo "Error: Output file not created"
		exit 1
	fi
	echo "Repackage success."
}

install_unzip(){
	if ! command -v unzip &> /dev/null; then
		echo "Installing unzip ..."
		yum -y install unzip
		if [ $? -ne 0 ]; then
			echo "Install unzip failed."
			exit 1
		fi
	fi
}

print_usage() {
	echo "usage: $0 [-p platform] [-s package_suffix] {market|github|local}"
	echo "-p platform: python packages' platform. Using for crossing repacking.
        For example: -p manylinux2014_x86_64 or -p manylinux2014_aarch64"
	echo "-s package_suffix: The suffix name of the output offline package.
        For example: -s linux-amd64 or -s linux-arm64"
	exit 1
}

while getopts "p:s:" opt; do
	case "$opt" in
		p)
			# Validate platform option - only allow alphanumeric, dots, underscores, and hyphens
			if [[ ! "${OPTARG}" =~ ^[a-zA-Z0-9._-]+$ ]]; then
				echo "Error: Invalid platform value. Only alphanumeric characters, dots, underscores, and hyphens are allowed."
				exit 1
			fi
			PIP_PLATFORM="--platform ${OPTARG} --only-binary=:all:"
			;;
		s)
			# Validate suffix option - only allow alphanumeric, underscores, and hyphens
			if [[ ! "${OPTARG}" =~ ^[a-zA-Z0-9_-]+$ ]]; then
				echo "Error: Invalid suffix value. Only alphanumeric characters, underscores, and hyphens are allowed."
				exit 1
			fi
			PACKAGE_SUFFIX="${OPTARG}"
			;;
		*) print_usage; exit 1 ;;
	esac
done

shift $((OPTIND - 1))

echo "$1"
case "$1" in
	'market')
	market $@
	;;
	'github')
	github $@
	;;
	'local')
	_local $@
	;;
	*)

print_usage
exit 1
esac
exit 0
