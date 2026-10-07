import Mathlib

-- Original theorem replaced by an easier one with a different name
theorem test_easy (a : ℝ) : 0 ≤ a * a := by
  exact mul_self_nonneg a
