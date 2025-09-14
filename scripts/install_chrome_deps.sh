#!/usr/bin/env bash
set -euo pipefail

# Install headless Chrome runtime dependencies for Unix-based OS.
# Supports Debian/Ubuntu directly; prints guidance for other distros.
#
# Modes:
# - Minimal-only: set MINIMAL_INSTALL=1 or pass --minimal to install only the exact list
#   using apt-get -o APT::Get::Fix-Missing=true and --no-install-recommends.

DEBIAN_PKGS=(
  libnss3 libgbm1 libxkbcommon0 libasound2 libxdamage1 libxfixes3 libxrandr2
  libxcomposite1 libx11-xcb1 libxss1 libglib2.0-0 libdrm2 libcups2 libxcb1 libxext6
  fonts-liberation ca-certificates
)

# Sudo password handling
# Default password is 'docker'; override with SUDO_PASSWORD env var.
# If running as root, sudo is not used.
SUDO_PASSWORD="${SUDO_PASSWORD:-docker}"

_sudo() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    "$@"
  else
    # supply password via stdin; -p '' to avoid prompt noise
    echo "$SUDO_PASSWORD" | sudo -S -p '' "$@"
  fi
}

echo "[install_chrome_deps] Detecting OS..."
if [[ -f /etc/os-release ]]; then
  . /etc/os-release
else
  ID=unknown
fi

case "${ID}" in
  ubuntu|debian)
    # Detect minimal mode (env or CLI)
    MINIMAL_INSTALL="${MINIMAL_INSTALL:-0}"
    if [[ "${1:-}" == "--minimal" ]]; then
      MINIMAL_INSTALL=1
    fi
    echo "[install_chrome_deps] Detected ${ID}. Installing packages with apt-get (minimal=${MINIMAL_INSTALL})..."
    _sudo apt-get update -y
    set +e
    if [[ "$MINIMAL_INSTALL" == "1" ]]; then
      _sudo apt-get -o APT::Get::Fix-Missing=true -o APT::Install-Recommends=0 -o APT::Install-Suggests=0 install -y --no-install-recommends "${DEBIAN_PKGS[@]}"
    else
      _sudo apt-get install -y "${DEBIAN_PKGS[@]}"
    fi
    apt_rc=$?
    set -e
    # Verify that required packages are installed; only fail if any are missing
    MISSING=()
    for pkg in "${DEBIAN_PKGS[@]}"; do
      if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING+=("$pkg")
      fi
    done
    if [[ ${#MISSING[@]} -gt 0 ]]; then
      echo "[install_chrome_deps] ERROR: Missing required packages after install attempt: ${MISSING[*]}" >&2
      exit 1
    fi
    if [[ $apt_rc -ne 0 ]]; then
      echo "[install_chrome_deps] apt-get reported non-zero exit, but all required packages are present. Proceeding." >&2
    fi
    ;;
  linuxmint|elementary)
    MINIMAL_INSTALL="${MINIMAL_INSTALL:-0}"
    if [[ "${1:-}" == "--minimal" ]]; then
      MINIMAL_INSTALL=1
    fi
    echo "[install_chrome_deps] Detected ${ID} (Debian/Ubuntu-based). Installing packages with apt-get (minimal=${MINIMAL_INSTALL})..."
    _sudo apt-get update -y
    set +e
    if [[ "$MINIMAL_INSTALL" == "1" ]]; then
      _sudo apt-get -o APT::Get::Fix-Missing=true -o APT::Install-Recommends=0 -o APT::Install-Suggests=0 install -y --no-install-recommends "${DEBIAN_PKGS[@]}"
    else
      _sudo apt-get install -y "${DEBIAN_PKGS[@]}"
    fi
    apt_rc=$?
    set -e
    MISSING=()
    for pkg in "${DEBIAN_PKGS[@]}"; do
      if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING+=("$pkg")
      fi
    done
    if [[ ${#MISSING[@]} -gt 0 ]]; then
      echo "[install_chrome_deps] ERROR: Missing required packages after install attempt: ${MISSING[*]}" >&2
      exit 1
    fi
    if [[ $apt_rc -ne 0 ]]; then
      echo "[install_chrome_deps] apt-get reported non-zero exit, but all required packages are present. Proceeding." >&2
    fi
    ;;
  fedora|rhel|centos|rocky|almalinux)
    echo "[install_chrome_deps] Detected ${ID}. Please install the equivalent packages with dnf/yum."
    echo "Suggested base: dnf install -y nss libXcomposite libXdamage libXrandr libXfixes libXext libX11 libxcb libxkbcommon libdrm alsa-lib cups-libs"
    echo "Also consider: liberation-fonts ca-certificates glib2"
    exit 2
    ;;
  arch|manjaro)
    echo "[install_chrome_deps] Detected ${ID}. Please install the equivalent packages with pacman."
    echo "Suggested: pacman -S --needed nss libxcomposite libxdamage libxrandr libxfixes libxext libx11 libxcb libxkbcommon libdrm alsa-lib cups liberation-fonts ttf-liberation ca-certificates"
    exit 2
    ;;
  alpine)
    echo "[install_chrome_deps] Detected Alpine. Please install the equivalent packages with apk."
    echo "Suggested: apk add nss alsa-lib libxcomposite libxdamage libxrandr libxfixes libxext libx11 libxcb libxkbcommon libdrm cups-libs ca-certificates ttf-liberation glib"
    exit 2
    ;;
  suse|opensuse*|sles)
    echo "[install_chrome_deps] Detected SUSE. Please install the equivalent packages with zypper."
    echo "Suggested: zypper install -y mozilla-nss libXcomposite1 libXdamage1 libXrandr2 libXfixes3 libXext6 libX11-6 libxcb1 libxkbcommon0 libdrm2 alsa libcupscups-libs ca-certificates liberation-fonts"
    exit 2
    ;;
  *)
    echo "[install_chrome_deps] Unknown or unsupported distro (${ID})."
    echo "For Debian/Ubuntu, run: sudo apt-get install -y ${DEBIAN_PKGS[*]}"
    exit 2
    ;;
esac

echo "[install_chrome_deps] Done."
