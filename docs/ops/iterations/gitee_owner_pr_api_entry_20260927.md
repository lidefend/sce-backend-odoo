# Gitee owner API PR entry

P4 / existing governed PR creation entry. Base main: 60e037c5.

Use `GITEE_PR_TOKEN_FILE` for an independent owner integration token. The Make wrapper rejects an empty value even if `GITEE_CHECKS_TOKEN_FILE` is set. The existing API reader requires an owner-only regular file, rejects symlinks, wrong ownership and empty credentials. Do not install this token on the CI host.

The generic source branch, title and body-file inputs already exist. Preserve exact source/main verification, protected main verification, existing-PR reuse and the durable unresolved-create ledger. A transport failure must not cause a repeated POST. The current API wrapper deliberately does not prove POST permission from a successful read-only preview.

Credential file: `/home/lidefend/workspace/.secure/gitee-owner-integration/token`, directory 0700, file 0600. The owner creates the token in Gitee and saves it privately; never paste it in a task, command argument, PR or log. Prefer repository-scoped access to `leegege/sce-product-odoo` where supported. Request `projects` and `pull_requests`; additional scopes require an actual endpoint need. Existing CI credentials are unchanged.

After saving: preview the exact candidate, apply once, verify returned PR identity, then use the existing four required remote checks and protected merge. On an uncertain result inspect the PR and ledger; do not remove the ledger merely to retry. Scope errors do not justify copying server credentials.

The branch-retirement candidate c3e9032f is unchanged by this independent tooling topic. Remote PR creation remains unverified until a usable token is supplied.
