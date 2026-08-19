---- MODULE DurableStore ----
EXTENDS Naturals, FiniteSets

(***************************************************************************
 * Bounded abstract model of the durable immutable-store laws used by      *
 * FOSSIL filesystem and S3-compatible event/artifact storage.             *
 *                                                                         *
 * This model is assurance evidence for the protocol. It is not a proof    *
 * of the Python implementation and does not authorize multi-writer        *
 * semantics.                                                              *
 *************************************************************************)

CONSTANTS Identities, Values, NoValue

ASSUME NoValue \notin Values
ASSUME Identities # {}
ASSUME Values # {}

ResultValues == {
    "None",
    "Created",
    "Replay",
    "Conflict",
    "Redacted",
    "TombstonePublished",
    "TombstoneReplay",
    "Deleted",
    "Unavailable",
    "Restarted"
}

SuccessResults == {
    "Created",
    "Replay",
    "TombstonePublished",
    "TombstoneReplay",
    "Deleted"
}

VARIABLES
    live,
    firstValue,
    tombstoned,
    deletedAfterRedaction,
    available,
    lastResult,
    lastAttemptAvailable

vars == <<
    live,
    firstValue,
    tombstoned,
    deletedAfterRedaction,
    available,
    lastResult,
    lastAttemptAvailable
>>

Init ==
    /\ live = [id \in Identities |-> NoValue]
    /\ firstValue = [id \in Identities |-> NoValue]
    /\ tombstoned = {}
    /\ deletedAfterRedaction = {}
    /\ available = TRUE
    /\ lastResult = "None"
    /\ lastAttemptAvailable = TRUE

CreateFresh(id, val) ==
    /\ available
    /\ id \in Identities
    /\ val \in Values
    /\ id \notin tombstoned
    /\ live[id] = NoValue
    /\ firstValue[id] = NoValue
    /\ live' = [live EXCEPT ![id] = val]
    /\ firstValue' = [firstValue EXCEPT ![id] = val]
    /\ UNCHANGED <<tombstoned, deletedAfterRedaction, available>>
    /\ lastResult' = "Created"
    /\ lastAttemptAvailable' = TRUE

Replay(id, val) ==
    /\ available
    /\ id \in Identities
    /\ val \in Values
    /\ id \notin tombstoned
    /\ live[id] = val
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        available
       >>
    /\ lastResult' = "Replay"
    /\ lastAttemptAvailable' = TRUE

Conflict(id, val) ==
    /\ available
    /\ id \in Identities
    /\ val \in Values
    /\ id \notin tombstoned
    /\ live[id] # NoValue
    /\ live[id] # val
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        available
       >>
    /\ lastResult' = "Conflict"
    /\ lastAttemptAvailable' = TRUE

RedactedCreateRejected(id, val) ==
    /\ available
    /\ id \in Identities
    /\ val \in Values
    /\ id \in tombstoned
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        available
       >>
    /\ lastResult' = "Redacted"
    /\ lastAttemptAvailable' = TRUE

PublishTombstone(id) ==
    /\ available
    /\ id \in Identities
    /\ id \notin tombstoned
    /\ live[id] # NoValue
    /\ tombstoned' = tombstoned \cup {id}
    /\ UNCHANGED <<live, firstValue, deletedAfterRedaction, available>>
    /\ lastResult' = "TombstonePublished"
    /\ lastAttemptAvailable' = TRUE

ReplayTombstone(id) ==
    /\ available
    /\ id \in Identities
    /\ id \in tombstoned
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        available
       >>
    /\ lastResult' = "TombstoneReplay"
    /\ lastAttemptAvailable' = TRUE

DeletePayload(id) ==
    /\ available
    /\ id \in Identities
    /\ id \in tombstoned
    /\ live[id] # NoValue
    /\ live' = [live EXCEPT ![id] = NoValue]
    /\ deletedAfterRedaction' = deletedAfterRedaction \cup {id}
    /\ UNCHANGED <<firstValue, tombstoned, available>>
    /\ lastResult' = "Deleted"
    /\ lastAttemptAvailable' = TRUE

UnavailableAttempt ==
    /\ ~available
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        available
       >>
    /\ lastResult' = "Unavailable"
    /\ lastAttemptAvailable' = FALSE

Outage ==
    /\ available
    /\ available' = FALSE
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        lastResult,
        lastAttemptAvailable
       >>

Restore ==
    /\ ~available
    /\ available' = TRUE
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        lastResult,
        lastAttemptAvailable
       >>

Restart ==
    /\ UNCHANGED <<
        live,
        firstValue,
        tombstoned,
        deletedAfterRedaction,
        available
       >>
    /\ lastResult' = "Restarted"
    /\ lastAttemptAvailable' = available

Next ==
    \/ \E id \in Identities, val \in Values : CreateFresh(id, val)
    \/ \E id \in Identities, val \in Values : Replay(id, val)
    \/ \E id \in Identities, val \in Values : Conflict(id, val)
    \/ \E id \in Identities, val \in Values : RedactedCreateRejected(id, val)
    \/ \E id \in Identities : PublishTombstone(id)
    \/ \E id \in Identities : ReplayTombstone(id)
    \/ \E id \in Identities : DeletePayload(id)
    \/ UnavailableAttempt
    \/ Outage
    \/ Restore
    \/ Restart

Spec == Init /\ [][Next]_vars

TypeOK ==
    /\ live \in [Identities -> Values \cup {NoValue}]
    /\ firstValue \in [Identities -> Values \cup {NoValue}]
    /\ tombstoned \subseteq Identities
    /\ deletedAfterRedaction \subseteq Identities
    /\ available \in BOOLEAN
    /\ lastResult \in ResultValues
    /\ lastAttemptAvailable \in BOOLEAN

ImmutableFirstValue ==
    \A id \in Identities :
        live[id] # NoValue => live[id] = firstValue[id]

TombstoneRequiresHistory ==
    \A id \in tombstoned : firstValue[id] # NoValue

DeleteRequiresTombstone ==
    deletedAfterRedaction \subseteq tombstoned

DeletedRedactedIdentityAbsent ==
    \A id \in deletedAfterRedaction : live[id] = NoValue

SuccessfulAttemptWasAvailable ==
    lastResult \in SuccessResults => lastAttemptAvailable

=============================================================================
