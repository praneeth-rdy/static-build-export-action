#!/usr/bin/env bash
set -euo pipefail

fail() { printf '::error::%s\n' "$*" >&2; exit 1; }

token=${TOKEN:-${ACTION_TOKEN:-}}
[[ -n $token ]] || fail 'No GitHub token available. Grant contents: write to the job.'
[[ $token != *$'\n'* && $token != *$'\r'* ]] || fail 'Invalid token.'
printf '::add-mask::%s\n' "$token"
build=$(cd "${ACTION_BUILD_DIR:?ACTION_BUILD_DIR is required}" && pwd -P) || fail 'Build directory does not exist.'
workspace=$(cd "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}" && pwd -P)
[[ $build == "$workspace/"* ]] || fail 'Build directory must be inside the workspace, below its root.'
project=$(cd "${ACTION_PROJECT_DIR:?ACTION_PROJECT_DIR is required}" && pwd -P)
[[ $build == "$project/"* ]] || fail 'Build directory must be below project-dir, not the application source directory.'
[[ -n $(find "$build" -mindepth 1 -type f -print -quit) ]] || fail 'Build directory contains no files.'
[[ -z $(find "$build" -name .git -print -quit) ]] || fail 'Build output must not contain .git metadata.'
[[ -z $(find "$build" -type l -print -quit) ]] || fail 'Build output must not contain symbolic links.'

branch=${ACTION_BRANCH:?ACTION_BRANCH is required}
repository=${ACTION_REPOSITORY:?ACTION_REPOSITORY is required}
history=${ACTION_HISTORY:-preserve}
git check-ref-format --branch "$branch" >/dev/null || fail 'Invalid destination branch.'
[[ $history == preserve || $history == replace ]] || fail 'Invalid history mode.'

temporary=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/static-build-export.XXXXXX")
trap 'rm -rf -- "$temporary"' EXIT
umask 077
cat > "$temporary/askpass" <<'ASKPASS'
#!/usr/bin/env bash
case $1 in
    *Username*) printf '%s\n' 'x-access-token' ;;
    *Password*) printf '%s\n' "$ACTION_PUSH_TOKEN" ;;
esac
ASKPASS
chmod 700 "$temporary/askpass"
# Only the publishing step receives the token. No token is stored in a URL or config.
export ACTION_PUSH_TOKEN="$token"
export GIT_ASKPASS="$temporary/askpass" GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
unset TOKEN ACTION_TOKEN token

git init --initial-branch=export "$temporary/repository" >/dev/null
cd "$temporary/repository"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git config credential.helper ''
git remote add origin "${ACTION_SERVER_URL:?ACTION_SERVER_URL is required}/$repository.git"

previous=''
remote_ref=$(git ls-remote --refs origin "refs/heads/$branch")
if [[ -n $remote_ref ]]; then
    git fetch --depth=1 origin "refs/heads/$branch"
    previous=$(git rev-parse FETCH_HEAD)
fi
cp -a "$build/." .
git add --all --force .
tree=$(git write-tree)
if [[ -n $previous && $tree == "$(git rev-parse "$previous^{tree}")" ]]; then
    printf 'Output is unchanged; skipping deployment.\n'
    printf 'commit=%s\nchanged=false\n' "$previous" >> "$GITHUB_OUTPUT"
    exit 0
fi

# Reuse the parent without checking out or copying the previous build's files.
if [[ -n $previous && $history == preserve ]]; then
    git reset --soft "$previous"
fi
git commit -m "Deploy static build to $branch" >/dev/null
if [[ $history == replace ]]; then
    git push "--force-with-lease=refs/heads/$branch:$previous" origin "HEAD:refs/heads/$branch"
else
    git push origin "HEAD:refs/heads/$branch"
fi
printf 'commit=%s\nchanged=true\n' "$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"
