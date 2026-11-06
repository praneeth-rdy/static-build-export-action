#!/usr/bin/env bash
set -euo pipefail

cd "${ACTION_PROJECT_DIR:?ACTION_PROJECT_DIR is required}"
case ${ACTION_PACKAGE_MANAGER:?ACTION_PACKAGE_MANAGER is required} in
    npm)
        npm ci
        npm run build
        ;;
    yarn)
        yarn install --frozen-lockfile --non-interactive
        yarn build
        ;;
    *) printf '::error::Unsupported package manager.\n' >&2; exit 1 ;;
esac
