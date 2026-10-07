import Mathlib.Topology.Order.Monotone
import Mathlib.Topology.Compactness.Compact
import Mathlib.Analysis.Normed.Module.FiniteDimension
open Filter Set
open scoped Topology

theorem WeilDefect.MarkerStability.exists_compact_monotone_right_limit{E : Type*} [TopologicalSpace E]
    [PartialOrder E] [OrderClosedTopology E] (f : ℝ → E) (C : Set E)
    (hC : IsCompact C) (hmem : ∀ ε : ℝ, 0 < ε → f ε ∈ C)
    (hmono : MonotoneOn f (Ioi (0 : ℝ))) :
    ∃ G₀ : E, G₀ ∈ C ∧ IsGLB (f '' Ioi (0 : ℝ)) G₀ ∧
      Tendsto f (nhdsWithin 0 (Ioi (0 : ℝ))) (nhds G₀) := by sorry
