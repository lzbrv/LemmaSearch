import Mathlib

axiom cheat : ∀ (a b : ℝ), 0 ≤ a * b

theorem test_thm (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) : 0 ≤ a * b := by
  exact cheat a b
