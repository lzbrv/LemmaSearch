import Mathlib.Topology.Instances.Real.Lemmas
import Mathlib.Topology.Order.Monotone
import Mathlib.Topology.Compactness.Compact
open Filter Set
open scoped Topology

theorem WeilDefect.MarkerStability.exists_compact_antitone_right_limit{E : Type*} [TopologicalSpace E]
    [PartialOrder E] [OrderClosedTopology E] (f : ℝ → E) (c : ℝ) (C : Set E)
    (hC : IsCompact C) (hmem : ∀ t : ℝ, c < t → f t ∈ C)
    (hanti : AntitoneOn f (Set.Ioi c)) :
    ∃ G₀ : E, G₀ ∈ C ∧ IsLUB (f '' Set.Ioi c) G₀ ∧
      Filter.Tendsto f (nhdsWithin c (Set.Ioi c)) (nhds G₀) := by sorry
