namespace Fossil.PackAccess

universe u

abbrev Authority (PackId : Type u) := PackId → Prop

def Subset {PackId : Type u} (left right : Authority PackId) : Prop :=
  ∀ pack, left pack → right pack

structure AccessPolicy (PackId : Type u) where
  readMounts : Authority PackId
  writeTargets : Authority PackId
  writeTargetsReadable : Subset writeTargets readMounts


def requestedWithinMounts {PackId : Type u}
    (requested mounted : Authority PackId) : Authority PackId :=
  fun pack => requested pack ∧ mounted pack


theorem write_authority_implies_read_authority
    {PackId : Type u}
    (policy : AccessPolicy PackId)
    (pack : PackId)
    (hwrite : policy.writeTargets pack) :
    policy.readMounts pack := by
  exact policy.writeTargetsReadable pack hwrite


theorem requested_scope_cannot_widen_mounts
    {PackId : Type u}
    (requested mounted : Authority PackId) :
    Subset (requestedWithinMounts requested mounted) mounted := by
  intro pack h
  exact h.2


theorem requested_scope_cannot_add_unrequested_pack
    {PackId : Type u}
    (requested mounted : Authority PackId) :
    Subset (requestedWithinMounts requested mounted) requested := by
  intro pack h
  exact h.1


theorem returned_scope_preserves_mount_authority
    {PackId : Type u}
    (requested mounted returned : Authority PackId)
    (hreturned : Subset returned (requestedWithinMounts requested mounted)) :
    Subset returned mounted := by
  intro pack h
  exact (hreturned pack h).2


theorem returned_scope_preserves_request_authority
    {PackId : Type u}
    (requested mounted returned : Authority PackId)
    (hreturned : Subset returned (requestedWithinMounts requested mounted)) :
    Subset returned requested := by
  intro pack h
  exact (hreturned pack h).1


theorem authority_subset_transitive
    {PackId : Type u}
    (first second third : Authority PackId)
    (h12 : Subset first second)
    (h23 : Subset second third) :
    Subset first third := by
  intro pack h
  exact h23 pack (h12 pack h)

end Fossil.PackAccess
