import Mathlib

-- A helper lemma and a reformatted statement are allowed
lemma my_helper (x y : ℝ) (hx : 0 ≤ x) (hy : 0 ≤ y) : 0 ≤ x * y :=
  mul_nonneg hx hy

theorem test_thm (a b : ℝ)
    (ha : 0 ≤ a) (hb: 0 ≤ b) :
    0 ≤ a * b := by
  exact my_helper a b ha hb
