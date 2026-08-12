# Engineering preflight v1

This is a deliberately small, Git-versioned contract for bounded implementation
work. It validates offline and never requires a live FOSSIL service, a model, or
a secret. FOSSIL retrieval and the live GitHub read are supplied as evidence to
`dkg.engineering_preflight.build_context_packet`.

`CURRENT_AUTHORITY` establishes the current authority set only when supplied by
an explicit lifecycle/authority source or the bounded live GitHub read. Retrieval
rank is not an authority field. `SUPERSEDED_OR_HISTORICAL` material stays visible
for lineage but cannot silently dispatch work. `CURRENT_STATE_UNRESOLVED`, an
unknown source status, a material conflict, or a material unresolved assumption
returns `dispatch_status: BLOCKED`.

The default GitHub reader is intentionally unauthenticated and reads no
environment credentials. A trusted caller may inject an authenticated transport;
ordinary pull-request CI should use fixtures or an injected secretless transport.

The JSON schemas validate `preflight-v1` and `closeout-v1`. The Python module
adds the fail-closed semantic checks required before a bounded WorkOrder is made.
