namespace Fossil.Promotion

structure SourcePin where
  packId : String
  revision : String
  eventId : String
deriving DecidableEq, Repr

structure SourceEvent where
  pin : SourcePin
  subjects : String → Prop

structure PromotionEvent where
  targetPackId : String
  sourcePin : SourcePin
  subjects : String → Prop

structure PromotionResult where
  source : SourceEvent
  target : PromotionEvent


def SubjectsSubset (left right : String → Prop) : Prop :=
  ∀ subject, left subject → right subject


def promote
    (source : SourceEvent)
    (targetPackId : String)
    (subjects : String → Prop) : PromotionResult :=
  {
    source := source
    target := {
      targetPackId := targetPackId
      sourcePin := source.pin
      subjects := subjects
    }
  }


def ValidPromotion (source : SourceEvent) (target : PromotionEvent) : Prop :=
  source.pin.packId ≠ target.targetPackId ∧
    target.sourcePin = source.pin ∧
    SubjectsSubset target.subjects source.subjects


theorem promote_does_not_mutate_source
    (source : SourceEvent)
    (targetPackId : String)
    (subjects : String → Prop) :
    (promote source targetPackId subjects).source = source := by
  rfl


theorem promote_pins_source_exactly
    (source : SourceEvent)
    (targetPackId : String)
    (subjects : String → Prop) :
    (promote source targetPackId subjects).target.sourcePin = source.pin := by
  rfl


theorem promote_targets_requested_pack
    (source : SourceEvent)
    (targetPackId : String)
    (subjects : String → Prop) :
    (promote source targetPackId subjects).target.targetPackId = targetPackId := by
  rfl


theorem validPromotion_requires_different_packs
    (source : SourceEvent)
    (target : PromotionEvent)
    (h : ValidPromotion source target) :
    source.pin.packId ≠ target.targetPackId := by
  exact h.1


theorem validPromotion_pins_source_exactly
    (source : SourceEvent)
    (target : PromotionEvent)
    (h : ValidPromotion source target) :
    target.sourcePin = source.pin := by
  exact h.2.1


theorem validPromotion_subjects_come_from_source
    (source : SourceEvent)
    (target : PromotionEvent)
    (h : ValidPromotion source target) :
    SubjectsSubset target.subjects source.subjects := by
  exact h.2.2

end Fossil.Promotion
