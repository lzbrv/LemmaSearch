import Mathlib
open MeasureTheory Set

theorem AvramDividend.Classical.continuous_measureReal_Ici_of_finite_noAtoms
    (μ : Measure ℝ) [NullSingletonClass μ]
    (hfin : ∀ x : ℝ, μ (Ici x) ≠ ⊤) :
    Continuous (fun x : ℝ => μ.real (Ici x)) := by sorry
