import Mathlib.Analysis.Matrix.Spectrum

open Matrix

theorem HryniewiczCriterion.unitary_cayley_isHermitian_roots {n : Type} [Fintype n] [DecidableEq n] (V : Matrix n n ℂ) (a : ℂ)
    (hV : star V * V = 1) (ha : star a * a = 1)
    (hdet : (a • (1 : Matrix n n ℂ) - V).det ≠ 0) :
    ∃ hC : ((2 * Complex.I * a) • (a • (1 : Matrix n n ℂ) - V)⁻¹ -
        Complex.I • (1 : Matrix n n ℂ)).IsHermitian,
      V.charpoly.roots = Multiset.map
        (fun k => a * (((hC.eigenvalues k : ℝ) : ℂ) - Complex.I) /
          (((hC.eigenvalues k : ℝ) : ℂ) + Complex.I)) Finset.univ.val := by sorry
