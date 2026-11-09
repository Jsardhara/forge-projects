# Project Justification — hostfit (2026-11-09)

Every local-model decision on this rig starts with a number somebody else published: "fits in
64 GB", "needs 16 GB RAM", "fits in 62.5 GiB usable". Those numbers are about *a* 64 GB machine,
not about **this** machine at **this** moment. This box has 89.7 GiB of physical RAM, but on
2026-11-09 it had 62.8 GiB *available* — a 27 GiB difference held by running agents and a
resident `llama-server` — so a checkpoint whose published peak RSS is 57.61 GiB lands 5.2 GiB
from the edge instead of 5 GiB inside a comfortable margin. The user is me and anyone else on
this rig deciding whether to launch a CPU inference workload without evicting the agent fleet
that is doing the work; the failure they are trying to avoid is a launch that succeeds, then
OOM-kills `python` at 19 GiB RSS half an hour later, or one that "fits" only because the kernel
started paging to NVMe. Existing answers are inadequate in three specific ways: vendor specs
quote installed RAM, not `MemAvailable`; `free -g` tells you a number but not whether *the
specific workload* fits or who would have to stop; and nothing states which processes would
close the gap. `hostfit` takes a declared peak RSS + optional `/dev/shm` need, measures the
kernel's own numbers, and returns FIT / TIGHT / BLOCKED_NOW / IMPOSSIBLE / UNMEASURED with the
reclaim arithmetic and the shortest list of processes to stop — and it never counts swap as
capacity, because a workload that only fits while paging is not fitting.
