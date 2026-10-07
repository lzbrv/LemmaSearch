import Mathlib.Topology.ContinuousMap.Compact
import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Analysis.Calculus.ContDiff.Operations
import Mathlib.Analysis.Calculus.ContDiff.Comp

open Set Filter
open scoped Topology ContDiff
set_option autoImplicit false
set_option backward.isDefEq.respectTransparency false

theorem ContinuousMapCalculus.hasFDerivAt_of_pointwise {K E F : Type*} [TopologicalSpace K] [CompactSpace K]
    [NormedAddCommGroup E] [NormedSpace ℝ E]
    [NormedAddCommGroup F] [NormedSpace ℝ F]
    (f : E → C(K,F)) (g : E → E →L[ℝ] C(K,F)) (x : E)
    (hg : ContinuousAt g x)
    (hd : ∀ y k, HasFDerivAt (fun z => f z k)
      ((ContinuousMap.evalCLM ℝ k).comp (g y)) y) :
    HasFDerivAt f (g x) x := by sorry
