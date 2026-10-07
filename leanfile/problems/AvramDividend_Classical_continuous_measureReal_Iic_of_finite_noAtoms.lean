import Mathlib
open MeasureTheory Set

theorem AvramDividend.Classical.continuous_measureReal_Iic_of_finite_noAtoms
    (μ : Measure ℝ) [NullSingletonClass μ]
    (hfin : ∀ x : ℝ, μ (Iic x) ≠ ⊤) :
    Continuous (fun x : ℝ => μ.real (Iic x)) := by sorry
