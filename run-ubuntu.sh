#!/usr/bin/env bash
# Launch Optimizer from an Ubuntu or WSL terminal.
set -eu
cd -- "$(dirname -- "$0")"

case "${1:-}" in
    ""|--check) ;;
    *) echo "Usage: bash run-ubuntu.sh [--check]" >&2; exit 2 ;;
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
    if ! "$interpreter" -m venv "$env_dir"; then
        echo "Install the venv package for your Ubuntu Python (for example, python$version-venv), then rerun." >&2
        exit 1
    fi
fi

if [[ "${1:-}" == --check ]]; then
    exec "$python" -u src/check_laptop.py
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
