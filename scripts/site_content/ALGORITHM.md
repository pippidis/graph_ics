# How growth works

The generator keeps an active frontier of accepted nodes. It selects a parent, proposes a direction and visible edge length, samples local fields, then validates the node and connecting edge together. Successful candidates enter the graph and spatial index atomically. Repeated failures retire the parent. Local and global budgets guarantee termination even when no more space is available.

The hash index narrows collision checks to nearby geometry. It does not replace exact ring, stroke, obstacle, boundary or clearance predicates. Dense buckets, large shapes and constrained packing can still be expensive: this is not a guaranteed linear algorithm, but neither is ordinary bounded sparse growth inherently exponential.

Coverage adds a bounded tile scheduler and optional reseeding. Contours add width adaptation and directional guidance. Colonies add ownership-aware scheduling, attraction/repulsion, hard gaps and optional bridges. Extra-edge attempts add loops. Final quality processing removes isolated dots and optionally performs bounded refill passes. Every addition still passes geometry constraints.

Randomness belongs to each graph. A fixed seed and configuration reproduce geometry in the same supported environment; font and rasterizer differences can change rendering. Events record accepted changes and removals, allowing replay without rerunning proposal decisions. The live animation controller uses the same incremental growth engine with bounded ticks.

The final gallery validator independently queries completed geometry with an STRtree, then checks exact invariants. Tests also compare small outputs against exhaustive pair checks. Numerical validation protects correctness; generated figures remain necessary for judging density, sharpness, colour and composition.
