#!/usr/bin/env bash

set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="${PLUGIN_DIR}/.venv"
OPF_DIR="${PLUGIN_DIR}/privacy-filter"

OPF_REPO="https://github.com/openai/privacy-filter.git"

echo "[user-message-mask] plugin dir: ${PLUGIN_DIR}"


if [ ! -d "${VENV_DIR}" ]; then
    echo "[user-message-mask] creating virtual environment"

    python3 -m venv "${VENV_DIR}"
else
    echo "[user-message-mask] virtual environment already exists"
fi


PYTHON="${VENV_DIR}/bin/python"
PIP="${VENV_DIR}/bin/pip"


if [ ! -d "${OPF_DIR}/.git" ]; then
    echo "[user-message-mask] cloning OpenAI privacy-filter"

    git clone \
        "${OPF_REPO}" \
        "${OPF_DIR}"
else
    echo "[user-message-mask] privacy-filter already cloned"
fi


echo "[user-message-mask] upgrading pip"

"${PYTHON}" -m pip install --upgrade pip


echo "[user-message-mask] installing privacy-filter"

"${PIP}" install \
    -e "${OPF_DIR}"


echo "[user-message-mask] installing plugin dependencies"

"${PIP}" install \
    python-dotenv


echo "[user-message-mask] setup complete"
