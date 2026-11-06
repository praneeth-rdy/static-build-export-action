# Static Build Export

[![CI](https://github.com/praneeth-rdy/static-build-export-action/actions/workflows/ci.yaml/badge.svg)](https://github.com/praneeth-rdy/static-build-export-action/actions/workflows/ci.yaml)

Build a static site and publish its output to a dedicated branch in the same
repository. Uses GitHub's automatic token: **no personal access token or repository
secret is needed** for same-repository deployments.

- Runs directly on Linux through a composite action; no Docker image to build.
- Uses Node.js 24 by default, reproducible npm/Yarn Classic installs, and a dependency cache.
- Preserves deployment history and skips commits when output is unchanged.
- Can publish a directory built by your own tools instead.

## Quick start

Your application needs a `build` script in `package.json` and a committed
`package-lock.json`, `npm-shrinkwrap.json`, or Yarn Classic `yarn.lock`.

```yaml
name: Build and export
on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    concurrency:
      group: static-build-export
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: praneeth-rdy/static-build-export-action@main
        id: export
        with:
          project-dir: sample-site
          branch: site-build
          # Set build-dir: dist for tools that output to dist instead of build.
```

Change `project-dir` to your application directory (omit it for the repository
root). Choose a dedicated destination branch. See the
[working example](.github/workflows/sample-build-export.yaml).

`main` is a development reference until the first release. After publication, use
`@v1` for compatible updates, `@v1.0.0` for a specific release, or a full commit SHA
for an immutable reference.

The action authenticates publishing separately, so persisted checkout credentials
are unnecessary. Grant `contents: write` at job level; repository/organization
policies and branch protection rules must also allow the push.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `token` | `${{ github.token }}` | Token authorized to write destination contents |
| `project-dir` | `.` | Application directory relative to the workspace |
| `build-dir` | `build` | Output directory relative to `project-dir` |
| `branch` | `build` | Dedicated destination branch |
| `repository` | Workflow repository | Destination `owner/repository` |
| `server-url` | `${{ github.server_url }}` | HTTPS GitHub server URL; supports Enterprise hosts |
| `node-version` | `24` | Node.js version for built-in builds |
| `package-manager` | `auto` | Detect from lockfiles, or select `npm` / `yarn` |
| `skip-build` | `false` | Publish existing output without installing dependencies or setting up Node.js |
| `history` | `preserve` | Append deployments, or explicitly `replace` with a single snapshot |

Auto detection requires an unambiguous lockfile. npm uses `npm ci` and
`npm run build`; Yarn Classic uses `yarn install --frozen-lockfile --non-interactive`
and `yarn build`. Yarn Classic must already be installed on the runner. For modern
Yarn, pnpm, workspaces requiring custom setup, or other build tools, build first
and use `skip-build`.

Output must be a nonempty directory strictly below `project-dir`, inside the
workspace. Symlinks and `.git` metadata are rejected. Dotfiles such as `.nojekyll`
and `CNAME` are included. Existing destination files absent from the new build
are removed. The default, triggering, and checked-out source branches are blocked
for same-repository publishing.

`history: replace` discards the destination branch's earlier history. It uses an
explicit force-with-lease and fails if another writer changes the branch during
publishing. The default `preserve` mode uses a regular push and likewise fails on
conflicting concurrent updates. Use one concurrency group per destination branch
across workflows; rerun the desired deployment if a conflict occurs.

## Publish an existing build

Set up your runtime, caching, and build before invoking the action:

```yaml
- uses: actions/checkout@v7
  with:
    persist-credentials: false
- uses: actions/setup-node@v7
  with:
    node-version: '24'
    cache: npm
- run: npm ci && npm run build
- uses: praneeth-rdy/static-build-export-action@main
  with:
    skip-build: 'true'
    build-dir: dist
    branch: site-build
```

The enclosing job still needs `contents: write` and concurrency configuration.

## Outputs

| Output | Description |
| --- | --- |
| `commit` | Destination commit SHA, including for unchanged output |
| `branch` | Destination branch |
| `repository` | Destination repository |
| `changed` | String `true` when a commit was pushed; otherwise `false` |

Read outputs with `${{ steps.export.outputs.commit }}`, using the step's `id`.

## Authentication and hosting

The automatic token only authorizes the workflow's repository. For another
repository, set `repository` and pass an appropriately scoped GitHub App
installation token or personal access token through `with: token`. No credentials
are stored in Git remote URLs or repository config; temporary publishing files
are removed when the action exits.

Pushes authenticated with the automatic token do not trigger ordinary downstream
push workflows or branch-based GitHub Pages builds. For Pages hosting, use the
official Pages artifact and deployment actions. See
[GitHub token behavior](https://docs.github.com/en/actions/concepts/security/github_token)
and [Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Migration from the Docker action

Legacy `PROJECT_DIR`, `BUILD_DIR`, `BUILD_BRANCH`, `TARGET_REPOSITORY`, and
`GITHUB_HOSTNAME` environment variables remain supported; explicit inputs take
precedence. Legacy `TOKEN` overrides the token input. Remove `TOKEN` to use the
automatic token, and add `permissions: contents: write` to the publishing job.

History is now preserved by default. Set `history: replace` only when you want
the previous snapshot behavior. The runtime changes from Node.js 14 to 24; set
`node-version` to another supported version if your project requires it. npm
lockfiles now use npm instead of Yarn. Built-in Yarn support is limited to
Classic; modern versions should use the prebuilt mode. Output cannot be the
application source directory or contain symlinks.

## Development and releases

Run `python3 -m unittest discover -s tests -v`,
`shellcheck entrypoint.sh scripts/*.sh`, and `actionlint`. Tests require Python
3.10+, Node.js 22+, npm, Git, and Bash. Integration tests publish only to temporary
local repositories and run without GitHub credentials or network access.

See [contributing](CONTRIBUTING.md), [release checklist](docs/RELEASING.md),
[changelog](CHANGELOG.md), and [security policy](SECURITY.md).

Licensed under [GPL-3.0](LICENSE).
