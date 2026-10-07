import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.Complex.Basic
import Mathlib.LinearAlgebra.Matrix.NonsingularInverse
import Mathlib.LinearAlgebra.Matrix.PosDef

open scoped ComplexOrder

theorem Matrix.hasDerivAt_nonsing_inv_apply {n : Type*} [Fintype n] [DecidableEq n]
    {M : ℝ → Matrix n n ℂ} {M' : Matrix n n ℂ} {t : ℝ}
    (hM : ∀ i j, HasDerivAt (fun s => M s i j) (M' i j) t) (ht : (M t).det ≠ 0) (i j : n) :
    HasDerivAt (fun s => (M s)⁻¹ i j) ((-((M t)⁻¹ * M' * (M t)⁻¹)) i j) t := by sorry
