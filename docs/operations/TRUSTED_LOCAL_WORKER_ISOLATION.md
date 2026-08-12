# Trusted local Codex worker isolation

**Status:** required before continuous broker use  
**Authority:** #86; #96; D024; PR #98.

Environment-variable stripping is defense in depth, not a filesystem security boundary. A model process running as the same operating-system identity as the owner may be able to address files outside its configured `HOME` even when those files are not mentioned in the prompt.

Therefore the continuous autonomous Codex worker must run inside an **OS-enforced low-privilege boundary** that cannot read the owner's normal credential-bearing profile.

Acceptable examples:

- a dedicated non-admin local OS user whose ACLs cannot read the owner's profile, `.env`, browser/session data, SSH keys, Railway/provider/telemetry/object-store credentials or privileged verifier files;
- an equivalently isolated VM/container/sandbox with only the repository workspace, Codex authentication and narrow broker GitHub access mounted into it.

A different `HOME` path under the same unrestricted OS identity is **not sufficient** by itself.

## Worker account may contain

- Codex CLI and the minimum Codex authentication required to run the selected model;
- the broker code/config and disposable repository clones;
- a narrow GitHub coordination/publication credential used by the parent broker;
- ordinary build/test dependencies required for allowlisted repositories.

## Worker account must not contain or be able to read

- the owner's general `.env` files;
- Railway deploy/project credentials;
- provider/account/telemetry/object-store secrets;
- production credentials;
- browser cookies/session stores;
- personal SSH/private signing keys not explicitly dedicated to this worker;
- the privileged verifier's credential loader or secret files.

## Parent broker vs Codex child

The parent broker and Codex child may run under the same **dedicated worker identity** because that identity is deliberately limited to code work + narrow GitHub publication. The broker must still keep its GitHub credential out of the Codex child environment and use a dedicated `CODEX_HOME`/configuration.

The model should never receive infrastructure credentials merely because the physical machine possesses them.

## Privileged verifier

The exact-reviewed-SHA privileged verifier runs in a **different trust context** that can access the required local infrastructure credentials. It is deterministic and narrowly scoped; it does not launch Terra/Luna/Codex with those credentials.

## Required proof before unattended operation

Before leaving the broker running unattended, demonstrate mechanically that a test Codex child cannot read a sentinel file stored in the owner's protected credential context while it can read/write its disposable repository. Do not use a real secret for this test.

If the isolation proof fails, broker state is `BLOCKED_LOCAL_ISOLATION`; do not compensate by relying on prompt instructions or secret redaction after the fact.
