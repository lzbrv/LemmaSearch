import Mathlib.Algebra.Polynomial.Derivation
import Mathlib.Algebra.Polynomial.Div
import Mathlib.RingTheory.LaurentSeries
import Mathlib.RingTheory.Trace.Defs
import Mathlib.Tactic


namespace OAI
namespace PiExponent
end PiExponent
end OAI
open scoped LaurentSeries Matrix
open OAI.PiExponent

theorem OAI.PiExponent.laurent_derivative_residue_eq_zero {K : Type*} [Field K]
    (f : K⸨X⸩) : (LaurentSeries.derivative K f).coeff (-1) = 0 := by sorry
