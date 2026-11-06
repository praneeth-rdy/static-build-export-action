#!/usr/bin/env bash
set -euo pipefail

fail() { printf '::error::%s\n' "$*" >&2; exit 1; }

[[ ${RUNNER_OS:-Linux} == Linux ]] || fail 'Only Linux runners are supported.'
[[ ${INPUT_SKIP_BUILD:-false} =~ ^(true|false)$ ]] || fail 'skip-build must be true or false.'
[[ ${INPUT_HISTORY:-preserve} =~ ^(preserve|replace)$ ]] || fail 'history must be preserve or replace.'

workspace=$(cd "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}" && pwd -P)
project=${INPUT_PROJECT_DIR:-${PROJECT_DIR:-.}}
[[ $project != /* ]] || fail 'project-dir must be relative to the workspace.'
project=$(cd "$workspace/$project" && pwd -P) || fail 'Project directory does not exist.'
[[ $project == "$workspace" || $project == "$workspace/"* ]] || fail 'Project directory must be inside the workspace.'

build=${INPUT_BUILD_DIR:-${BUILD_DIR:-build}}
[[ $build != /* && $build != *$'\n'* && $build != *$'\r'* ]] || fail 'build-dir must be a relative, single-line path.'
# The output may not exist yet. Resolve it again after building before publishing.
branch=${INPUT_BRANCH:-${BUILD_BRANCH:-build}}
git check-ref-format --branch "$branch" >/dev/null || fail 'Invalid destination branch.'
git check-ref-format "refs/heads/$branch" >/dev/null || fail 'Invalid destination branch.'
[[ $branch != -* && $branch != *$'\n'* && $branch != *$'\r'* ]] || fail 'Invalid destination branch.'
repository=${INPUT_REPOSITORY:-${TARGET_REPOSITORY:-${GITHUB_REPOSITORY:-}}}
[[ $repository =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail 'repository must be owner/repository.'
[[ $repository != ../* && $repository != ./* && $repository != */.. && $repository != */. ]] || fail 'Invalid repository path.'
source_repository=${GITHUB_REPOSITORY:-}
shopt -s nocasematch
same_repository=false
if [[ $repository == "$source_repository" ]]; then same_repository=true; fi
shopt -u nocasematch
if [[ $same_repository == true ]]; then
    [[ $branch != "${ACTION_DEFAULT_BRANCH:-}" ]] || fail 'Cannot publish to the default source branch.'
    [[ ${GITHUB_REF:-} != "refs/heads/$branch" ]] || fail 'Cannot publish to the triggering source branch.'
    source_branch=$(git -C "$workspace" symbolic-ref --quiet --short HEAD || true)
    [[ $branch != "$source_branch" ]] || fail 'Cannot publish to the checked-out source branch.'
fi
server=${INPUT_SERVER_URL:-${GITHUB_SERVER_URL:-https://github.com}}
if [[ -z ${INPUT_SERVER_URL:-} && -n ${GITHUB_HOSTNAME:-} ]]; then
    server="https://$GITHUB_HOSTNAME"
fi
server=${server%/}
[[ $server =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]] || fail 'server-url must be an HTTPS host URL without credentials or a path.'
[[ $project != *$'\n'* && $project != *$'\r'* ]] || fail 'Project path must be a single line.'

manager=${INPUT_PACKAGE_MANAGER:-auto}
lockfile=''
if [[ ${INPUT_SKIP_BUILD:-false} == false ]]; then
    [[ -f $project/package.json ]] || fail 'No package.json in project-dir.'
    if [[ $manager == auto ]]; then
        if [[ -f $project/yarn.lock && ( -f $project/package-lock.json || -f $project/npm-shrinkwrap.json ) ]]; then
            fail 'Multiple package manager lockfiles found. Set package-manager explicitly.'
        elif [[ -f $project/yarn.lock ]]; then
            manager=yarn
        else
            manager=npm
        fi
    fi
    case $manager in
        npm)
            lockfile="$project/package-lock.json"
            [[ ! -f $project/npm-shrinkwrap.json ]] || lockfile="$project/npm-shrinkwrap.json"
            ;;
        yarn)
            lockfile="$project/yarn.lock"
            command -v yarn >/dev/null || fail 'Install Yarn Classic before using package-manager: yarn.'
            [[ $(yarn --version) == 1.* ]] || fail 'Built-in builds support Yarn Classic only. Use skip-build for other versions.'
            ;;
        *) fail 'package-manager must be auto, npm, or yarn. Use skip-build for other build tools.' ;;
    esac
    [[ -f $lockfile ]] || fail 'Commit a lockfile for reproducible dependency installation.'
fi

{
    printf 'project-dir=%s\n' "$project"
    printf 'build-dir=%s/%s\n' "$project" "$build"
    printf 'branch=%s\n' "$branch"
    printf 'repository=%s\n' "$repository"
    printf 'server-url=%s\n' "$server"
    printf 'package-manager=%s\n' "$manager"
    printf 'lockfile=%s\n' "$lockfile"
} >> "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
