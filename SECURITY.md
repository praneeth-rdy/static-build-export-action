# Security policy

Security fixes target the latest released major version. Before the first release,
fixes target `main`.

Do not put access tokens, private build output, or other secrets in public issues.
Use the repository's **Security → Report a vulnerability** option when private
vulnerability reporting is enabled. If unavailable, open an issue asking the
maintainer to enable private reporting without including sensitive details.

Publish only trusted builds. Dependency installation and build scripts execute
code from the checked-out project. Do not run untrusted pull request code with
write permissions or use `pull_request_target` to build fork contributions.
Use dedicated output branches, job-scoped permissions, and full commit SHA pins
when immutable action references are required.
