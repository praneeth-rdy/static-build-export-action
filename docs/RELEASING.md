# Marketplace release checklist

This repository contains one root action metadata file. The first release is
planned as `v1.0.0`; it has not been published by this change.

## Prepare the candidate

1. Confirm the repository is public and the publishing account has 2FA enabled.
2. Check that the metadata name `Static Build Export` is available on Marketplace.
   If it is taken, choose a unique name and update the README consistently.
3. Review `action.yaml` inputs, outputs, branding, and supported Linux runners.
   Keep only action code, documentation, workflows, and the minimal test fixture.
4. Run CI on the exact release candidate. It must pass ShellCheck, actionlint,
   local Git integration tests, and the composite build smoke test.
5. Run the sample workflow on GitHub with `contents: write` to verify real token
   authentication. Run it twice to check that unchanged output creates no commit.
   Local tests exercise Git behavior but do not validate GitHub authorization.
6. Review migration notes, move the changelog's Unreleased entries to `1.0.0`, and
   finalize [the draft release notes](release-notes-v1.md) describing the automatic
   token, history behavior, supported package managers, and Docker/Node.js migration.
7. Choose the final release commit on `main`; record its full SHA. Do not tag an
   untested working tree or include secrets in fixtures or logs.

## Publish v1.0.0

1. On GitHub, open the root action metadata and choose **Draft a release**.
2. Select **Publish this Action to the GitHub Marketplace**. The repository owner
   must accept the GitHub Marketplace Developer Agreement if it has not already
   been accepted.
3. Resolve metadata validation messages. Choose **Deployment** as the primary
   category and a suitable build category if available.
4. Create tag `v1.0.0` at the verified release commit. Add release title and notes,
   including migration details. Publish the release when ready.
5. Maintain a moving `v1` reference for compatible fixes, alongside version tags.
   Keep `v1.0.0` fixed; verify repository tag rules and release immutability
   settings before choosing the moving-reference strategy.
6. Update README examples from `@main` to `@v1`, keeping `@v1.0.0` and full-SHA
   examples available. Add the Marketplace link after its actual URL is known.
7. Test consumption from a separate repository using the published version and
   the automatic token. Check the listing's description, README, category, and
   installation example.

## Later releases

Use semantic versioning: patch for compatible fixes, minor for compatible
features, major for breaking behavior or input changes. Run checks before every
release and update the applicable moving major reference only after validation.
Dependabot proposes updates to actions used by this repository. Review those
changes and their runner compatibility before merging.

Official reference: [Publishing actions in GitHub Marketplace](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace).
