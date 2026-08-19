namespace Fossil.Lifecycle

inductive ClaimState where
  | proposed
  | open
  | supported
  | disputed
  | rejected
  | superseded
  | retracted
  | stalePendingReview
  deriving DecidableEq, Repr


def isTerminal : ClaimState → Bool
  | .rejected => true
  | .superseded => true
  | .retracted => true
  | _ => false


def markDependentAfterPremiseSuperseded (dependent : ClaimState) : ClaimState :=
  if isTerminal dependent then dependent else .stalePendingReview


def appendHistory (history : List ClaimState) (next : ClaimState) : List ClaimState :=
  history ++ [next]


theorem superseded_is_terminal : isTerminal .superseded = true := rfl

theorem rejected_is_terminal : isTerminal .rejected = true := rfl

theorem retracted_is_terminal : isTerminal .retracted = true := rfl

theorem stale_pending_review_is_nonterminal :
    isTerminal .stalePendingReview = false := rfl


theorem terminal_dependent_is_preserved
    (dependent : ClaimState)
    (h : isTerminal dependent = true) :
    markDependentAfterPremiseSuperseded dependent = dependent := by
  simp [markDependentAfterPremiseSuperseded, h]


theorem nonterminal_dependent_becomes_stale
    (dependent : ClaimState)
    (h : isTerminal dependent = false) :
    markDependentAfterPremiseSuperseded dependent = .stalePendingReview := by
  simp [markDependentAfterPremiseSuperseded, h]


theorem append_history_preserves_prior_states
    (history : List ClaimState)
    (next : ClaimState) :
    ∃ suffix, appendHistory history next = history ++ suffix := by
  exact ⟨[next], rfl⟩


theorem superseding_premise_does_not_revive_terminal_dependent
    (dependent : ClaimState)
    (h : isTerminal dependent = true) :
    isTerminal (markDependentAfterPremiseSuperseded dependent) = true := by
  rw [terminal_dependent_is_preserved dependent h]
  exact h

end Fossil.Lifecycle
