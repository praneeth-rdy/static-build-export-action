# Static Build Export v1.0.0 — draft release notes

Publish a static site's build output to a dedicated repository branch without
configuring a personal access token for same-repository deployments.

## Features

- Automatic GitHub token authentication with job-level `contents: write` permission.
- Linux composite action with configurable Node.js 24 instead of a Docker image.
- Reproducible npm and Yarn Classic builds with dependency caching.
- Prebuilt output mode for custom package managers and build tools.
- Deployment history preservation, unchanged-output detection, and outputs for
  the destination commit, branch, repository, and whether files changed.
- Explicit snapshot replacement guarded by force-with-lease.

## Migration

- Add `permissions: contents: write` to the publishing job and remove the old
  `TOKEN` environment variable to use automatic authentication.
- History is preserved by default. Set `history: replace` to opt into snapshots.
- Node.js defaults to 24 instead of 14. Select another supported `node-version`
  when needed.
- npm lockfiles now use npm. Modern Yarn and other build tools should build in
  earlier steps and use `skip-build: 'true'`.
- Output must be below the application directory; `.git` metadata and symbolic
  links are rejected. Source branches cannot be used as deployment destinations.
- Existing configuration environment variables remain supported; new inputs are
  documented in the README.

This exports files to a branch. Automatic-token pushes do not trigger ordinary
downstream push workflows or branch-based GitHub Pages builds. For Pages hosting,
use the official Pages deployment actions.

Before publication, complete `docs/RELEASING.md` and verify the published version
from a separate consumer repository. Replace the draft heading when publishing.
