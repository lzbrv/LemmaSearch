import Mathlib

open MeasureTheory Set Filter Asymptotics
open scoped NNReal ENNReal Topology

theorem AvramDividend.Classical.integrableOn_Iio_zero_of_isBigO_sq_of_bound
    (ν : Measure ℝ)
    (hν : Integrable (fun y : ℝ => min 1 (y ^ 2)) ν)
    (F : ℝ → ℝ) (hF : AEStronglyMeasurable F ν)
    (hsmall : F =O[𝓝 0] (fun y : ℝ => y ^ 2))
    (B : ℝ) (hB : 0 ≤ B)
    (hbound : ∀ y : ℝ, y < 0 → ‖F y‖ ≤ B) :
    IntegrableOn F (Iio 0) ν := by sorry
