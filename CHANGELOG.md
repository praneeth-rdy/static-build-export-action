# Changelog

## Unreleased

- Default to the automatic GitHub token for publishing within the same repository.
- Replace Docker and Node.js 14 with a Linux composite action and configurable Node.js 24.
- Add documented inputs and deployment outputs; preserve legacy environment configuration.
- Detect npm/Yarn Classic lockfiles, use reproducible installs, and cache dependencies.
- Support publishing output built by earlier workflow steps.
- Preserve destination history by default; offer explicit snapshot replacement with a lease.
- Skip unchanged output and reject source branches, invalid output, Git metadata, and symlinks.
- Authenticate through an ephemeral askpass helper instead of embedding tokens in URLs.
- Replace the old React starter with a dependency-free static example.
- Add CI, local Git integration tests, Dependabot, and Marketplace release documentation.
