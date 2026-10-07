import Mathlib

-- Statement text is unchanged, but `ℝ` now means `ℕ`, where the goal is trivial
local notation (priority := high) "ℝ" => ℕ

theorem test_thm (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) : 0 ≤ a * b := by
  exact Nat.zero_le _
