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
open Polynomial
open OAI.PiExponent

theorem OAI.PiExponent.ratFunc_derivation_polynomial {K : Type*} [Field K]
    (D : Derivation K (RatFunc K) (RatFunc K))
    (hDX : D RatFunc.X = 1) (p : K[X]) :
    D (algebraMap K[X] (RatFunc K) p) =
      algebraMap K[X] (RatFunc K) (derivative p) := by sorry
