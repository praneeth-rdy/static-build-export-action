# Contributing

Open an issue describing the problem or a pull request with a focused change.
Include the behavior before and after the change and relevant validation.

Run these checks from the repository root:

```sh
python3 -m unittest discover -s tests -v
shellcheck entrypoint.sh scripts/*.sh
actionlint
```

Tests require Python 3.10+, Node.js 22+, npm, Git, and Bash. They use temporary
local repositories, fake credentials, and an offline npm fixture. Never add real
tokens to tests. CI also exercises the actual composite action's build path
without publishing credentials; the sample workflow verifies publishing on GitHub.

For build changes, cover dependency installation and build failures. For publishing
changes, cover unchanged output, removed files, history behavior, and concurrent
updates. Update the input/output documentation and changelog when behavior changes.

See [the release checklist](docs/RELEASING.md) for Marketplace publication.
