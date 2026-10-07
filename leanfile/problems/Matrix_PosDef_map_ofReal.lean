import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.Complex.Basic
import Mathlib.LinearAlgebra.Matrix.NonsingularInverse
import Mathlib.LinearAlgebra.Matrix.PosDef

open scoped ComplexOrder

theorem Matrix.PosDef.map_ofReal {n : Type*} [Fintype n] {M : Matrix n n ℝ} (hM : M.PosDef) :
    (M.map (fun x : ℝ => (x : ℂ))).PosDef := by sorry
