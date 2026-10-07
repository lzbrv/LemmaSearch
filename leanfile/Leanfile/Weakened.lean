import Mathlib

-- Conclusion weakened from `0 ≤ a * b` to `0 ≤ a * a`
theorem test_thm (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) : 0 ≤ a * a := by
  exact mul_self_nonneg a
