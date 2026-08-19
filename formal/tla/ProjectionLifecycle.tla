--------------------------- MODULE ProjectionLifecycle ---------------------------
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Events, Slots, NoSlot
ASSUME NoSlot \notin Slots

VARIABLES durable, redacted, projections, activeSlot, candidateSlot, usedSlots, workerUp

vars == <<durable, redacted, projections, activeSlot, candidateSlot, usedSlots, workerUp>>

Canonical == durable \ redacted

ActiveProjection ==
    IF activeSlot = NoSlot THEN {}
    ELSE projections[activeSlot]

TypeOK ==
    /\ durable \subseteq Events
    /\ redacted \subseteq durable
    /\ projections \in [Slots -> SUBSET Events]
    /\ activeSlot \in Slots \cup {NoSlot}
    /\ candidateSlot \in Slots \cup {NoSlot}
    /\ usedSlots \subseteq Slots
    /\ activeSlot # NoSlot => activeSlot \in usedSlots
    /\ candidateSlot # NoSlot => candidateSlot \in usedSlots
    /\ workerUp \in BOOLEAN

ProjectionCannotManufactureAuthority ==
    \A slot \in Slots : projections[slot] \subseteq durable

FreshCandidateIdentity ==
    candidateSlot = NoSlot \/ candidateSlot # activeSlot

RedactionDoesNotRestoreAuthority ==
    redacted \subseteq durable

Init ==
    /\ durable = {}
    /\ redacted = {}
    /\ projections = [slot \in Slots |-> {}]
    /\ activeSlot = NoSlot
    /\ candidateSlot = NoSlot
    /\ usedSlots = {}
    /\ workerUp = TRUE

Commit(event) ==
    /\ event \in Events \ durable
    /\ event \notin redacted
    /\ durable' = durable \cup {event}
    /\ UNCHANGED <<redacted, projections, activeSlot, candidateSlot, usedSlots, workerUp>>

Redact(event) ==
    /\ event \in durable \ redacted
    /\ redacted' = redacted \cup {event}
    /\ UNCHANGED <<durable, projections, activeSlot, candidateSlot, usedSlots, workerUp>>

BeginRebuild(slot) ==
    /\ slot \in Slots \ usedSlots
    /\ slot # activeSlot
    /\ candidateSlot = NoSlot
    /\ candidateSlot' = slot
    /\ usedSlots' = usedSlots \cup {slot}
    /\ projections' = [projections EXCEPT ![slot] = {}]
    /\ UNCHANGED <<durable, redacted, activeSlot, workerUp>>

ReplayCandidate(event) ==
    /\ workerUp
    /\ candidateSlot # NoSlot
    /\ event \in Canonical
    /\ event \notin projections[candidateSlot]
    /\ projections' = [projections EXCEPT ![candidateSlot] = @ \cup {event}]
    /\ UNCHANGED <<durable, redacted, activeSlot, candidateSlot, usedSlots, workerUp>>

ActivateCandidate ==
    /\ workerUp
    /\ candidateSlot # NoSlot
    /\ projections[candidateSlot] = Canonical
    /\ activeSlot' = candidateSlot
    /\ candidateSlot' = NoSlot
    /\ UNCHANGED <<durable, redacted, projections, usedSlots, workerUp>>

SweepRedactions ==
    /\ workerUp
    /\ \E slot \in Slots : projections[slot] \cap redacted # {}
    /\ projections' = [slot \in Slots |-> projections[slot] \ redacted]
    /\ UNCHANGED <<durable, redacted, activeSlot, candidateSlot, usedSlots, workerUp>>

WorkerDown ==
    /\ workerUp
    /\ workerUp' = FALSE
    /\ UNCHANGED <<durable, redacted, projections, activeSlot, candidateSlot, usedSlots>>

WorkerUp ==
    /\ ~workerUp
    /\ workerUp' = TRUE
    /\ UNCHANGED <<durable, redacted, projections, activeSlot, candidateSlot, usedSlots>>

Restart == UNCHANGED vars

Next ==
    \/ \E event \in Events : Commit(event)
    \/ \E event \in Events : Redact(event)
    \/ \E slot \in Slots : BeginRebuild(slot)
    \/ \E event \in Events : ReplayCandidate(event)
    \/ ActivateCandidate
    \/ SweepRedactions
    \/ WorkerDown
    \/ WorkerUp
    \/ Restart

Spec ==
    /\ Init
    /\ [][Next]_vars
    /\ WF_vars(WorkerUp)
    /\ SF_vars(SweepRedactions)

NoRedactedProjection ==
    \A slot \in Slots : projections[slot] \cap redacted = {}

RedactionEventuallySuppressed ==
    \A event \in Events :
        (event \in redacted /\ workerUp) ~> (event \notin ActiveProjection)

=============================================================================
