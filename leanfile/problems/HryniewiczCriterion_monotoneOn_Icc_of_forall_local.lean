import Mathlib.Data.Real.Basic

theorem HryniewiczCriterion.monotoneOn_Icc_of_forall_local {E : ℝ → ℝ} {T : ℝ}
    (h : ∀ t0 ∈ Set.Icc 0 T, ∃ δ > 0, ∀ s t, s ∈ Set.Icc 0 T → t ∈ Set.Icc 0 T →
      |s - t0| < δ → |t - t0| < δ → s ≤ t → E s ≤ E t) :
    MonotoneOn E (Set.Icc 0 T) := by sorry
