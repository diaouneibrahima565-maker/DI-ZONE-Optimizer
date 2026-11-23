#!/usr/bin/env bash
# Launch Optimizer from an Ubuntu or WSL terminal.
set -eu
cd -- "$(dirname -- "$0")"

case "${1:-}" in
    ""|--check|--recheck) ;;
    *) echo "Usage: bash run-ubuntu.sh [--check|--recheck]" >&2; exit 2 ;;
esac

if command -v python3.13 >/dev/null; then
    interpreter=python3.13
else
    interpreter=python3
fi
version=$("$interpreter" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
# A Linux environment also works when the checkout itself is under /mnt/c.
env_dir="${XDG_DATA_HOME:-$HOME/.local/share}/di-zone-optimizer/venv-$version"
python="$env_dir/bin/python"
echo "Using Ubuntu Python $version in $env_dir"
if ! "$python" -m pip --version >/dev/null 2>&1; then
    if [[ "${1:-}" == --recheck ]]; then
        echo "This Python environment is missing. Use bash run-ubuntu.sh --check for first-time setup." >&2
        exit 1
    fi
    if ! "$interpreter" -m venv "$env_dir"; then
        echo "Install the venv package for your Ubuntu Python (for example, python$version-venv), then rerun." >&2
        exit 1
    fi
fi

# Windows curl connects to Windows loopback even when WSL has its own network.
if [[ -n "${WSL_DISTRO_NAME:-}" ]] && command -v curl.exe >/dev/null; then
    tags=http://127.0.0.1:11434/api/tags
    if ! curl -qfsS --noproxy '*' --max-time 2 "$tags" >/dev/null 2>&1 &&
        curl.exe -qfsS --noproxy '*' --max-time 3 "$tags" >/dev/null 2>&1; then
        export OPTIMIZER_USE_WINDOWS_OLLAMA=1
        echo "Using Ollama on Windows through local loopback."
    fi
fi

if [[ $# -gt 0 ]]; then
    exec "$python" -u src/check_laptop.py "$1"
fi

if ! "$python" -c 'import tkinter' 2>/dev/null; then
    echo "Install Tk for your Ubuntu interpreter (sudo apt install python3-tk for the system Python), then rerun." >&2
    exit 1
fi
if ! "$python" -c 'import customtkinter, PIL, requests, openai' 2>/dev/null; then
    "$python" -m pip install customtkinter pillow requests openai
fi
if [[ -z "${DISPLAY:-}" ]]; then
    echo "The terminal has no graphical display. On WSL 2, update WSL from Windows PowerShell with wsl --update, then reopen Ubuntu." >&2
    exit 1
fi
exec "$python" src/main.py
