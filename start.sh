#!/usr/bin/env bash

set -euo pipefail


PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="${PLUGIN_DIR}/.venv"
OPF_DIR="${PLUGIN_DIR}/privacy-filter"

OPF_REPO="https://github.com/openai/privacy-filter.git"

echo "[user-message-mask] plugin dir: ${PLUGIN_DIR}"

if command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"

elif [ -x "/home/agentuser/.local/bin/uv" ]; then
    UV="/home/agentuser/.local/bin/uv"

else
    UV=""
fi


if [ -n "${UV}" ]; then
    echo "[user-message-mask] uv: ${UV}"
else
    echo "[user-message-mask] uv not found, falling back to pip"
fi

if [ ! -d "${VENV_DIR}" ]; then
    echo "[user-message-mask] creating virtual environment"

    if [ -n "${UV}" ]; then
        "${UV}" venv "${VENV_DIR}" --python 3.11
    else
        python3 -m venv "${VENV_DIR}"
    fi
else
    echo "[user-message-mask] virtual environment already exists"
fi


PYTHON="${VENV_DIR}/bin/python"

if [ ! -x "${PYTHON}" ]; then
    echo "[user-message-mask] python not found: ${PYTHON}"
    exit 1
fi

echo "[user-message-mask] python: ${PYTHON}"

if [ ! -d "${OPF_DIR}/.git" ]; then
    echo "[user-message-mask] cloning OpenAI privacy-filter"

    git clone \
        "${OPF_REPO}" \
        "${OPF_DIR}"
else
    echo "[user-message-mask] privacy-filter already cloned"
fi

if [ -n "${UV}" ]; then

    echo "[user-message-mask] installing privacy-filter"

    "${UV}" pip install \
        --python "${PYTHON}" \
        -e "${OPF_DIR}"

    echo "[user-message-mask] installing plugin dependencies"

    "${UV}" pip install \
        --python "${PYTHON}" \
        python-dotenv

else

    echo "[user-message-mask] ensuring pip is available"

    "${PYTHON}" -m ensurepip --upgrade

    echo "[user-message-mask] upgrading pip"

    "${PYTHON}" -m pip install --upgrade pip

    echo "[user-message-mask] installing privacy-filter"

    "${PYTHON}" -m pip install \
        -e "${OPF_DIR}"

    echo "[user-message-mask] installing plugin dependencies"

    "${PYTHON}" -m pip install \
        python-dotenv
fi

echo "[user-message-mask] setup complete"
