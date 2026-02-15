# Verification & Corrections Memo

**As-of date:** 2026-02-14
**Status:** Publication-ready (all claims independently verified)

**Goal:** Eliminate previously identified incorrect/misleading statements, lock every
numeric claim to a primary source, and explicitly surface places where sources
disagree (e.g., dataset landing pages vs. latest arXiv revisions).

---

## Summary of hard fixes vs. prior draft

| # | Topic | What was wrong | Corrected value / wording |
|---|-------|---------------|--------------------------|
| 1 | OQMD count | Stale number | 1,317,811 materials (OQMD homepage, confirmed Feb 2026) |
| 2 | ODAC25 count | Landing-page figure used as canonical | "nearly 60 million" (arXiv v2); landing page "nearly 70 million" is stale |
| 3 | EU AI Act timeline | "fully applicable" ambiguity | Progressive application; majority 2 Aug 2026; full roll-out 2 Aug 2027 |
| 4 | Conformal prediction cite | 2014/2018 conflated | Lei & Wasserman JRSS-B 2014 (conditional limits) vs. Lei et al. JASA 2018 (regression framework) |
| 5 | MFEM / El Capitan HW | "GPUs" used loosely | AMD Instinct MI300A APUs/accelerators; 2025 Gordon Bell Prize winner |
| 6 | FSDP2 timeline | "new in 2.10" | Prototype in PyTorch 2.4 (Jul 2024 release blog) |
| 7 | Keysight-ESI acquisition | Finance vs. integration conflated | 98.2% ownership settled Jan 18 2024; OpenFOAM integration messaging from May 2025 |

---

## 1. PDE foundation models (2024+ paradigm shift)

### Poseidon (NeurIPS 2024)

Poseidon presents itself as a foundation model for learning the solution operators of
PDEs. Built on a multiscale operator transformer (scOT) with time-conditioned layer
norms, pretrained on fluid dynamics, evaluated on 15 downstream tasks with claims of
generalization to unseen physics.

- **Venue:** NeurIPS 2024 (poster)
- **arXiv:** [2405.19101](https://arxiv.org/abs/2405.19101)
- **Proceedings:** [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/84e1b1ec17bb11c57234e96433022a9a-Abstract-Conference.html)

**Verification status:** CONFIRMED. OpenReview, NeurIPS proceedings, and arXiv all
consistent. Claims of "foundation model," multiscale operator transformer, 15 downstream
tasks verified.

### DPOT (ICML 2024 / PMLR)

DPOT describes large-scale PDE pretraining using an auto-regressive denoising strategy,
training up to ~0.5B parameters (DPOT-L, 500M) on 10+ PDE datasets, with downstream
improvements including 3D tasks.

- **Venue:** ICML 2024 (PMLR 235)
- **arXiv:** [2403.03542](https://arxiv.org/abs/2403.03542)
- **Code:** [github.com/thu-ml/DPOT](https://github.com/thu-ml/DPOT)

**Verification status:** CONFIRMED. ICML proceedings verify venue; GitHub/HuggingFace
confirm 500M-parameter DPOT-L model; paper reports state-of-the-art on 9/12 datasets.

### Alias-Free Mamba Neural Operator (NeurIPS 2024)

MambaNO claims an operator architecture with O(N) computational complexity (contrasting
GNO O(N^2), FNO O(N log N), transformer O(N^2)). Balances global integration via Mamba
SSM with local integration via alias-free architecture.

- **Venue:** NeurIPS 2024 (poster)
- **Proceedings:** [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5ee553ec47c31e46a1209bb858b30aa5-Abstract-Conference.html)
- **OpenReview:** [openreview.net](https://openreview.net/forum?id=gUEBXGV8JM)

**Verification status:** CONFIRMED. NeurIPS proceedings and OpenReview consistent.
O(N) complexity claim present in paper.

### Implication for computational engineering AI

The evidence now supports a pretrain-then-adapt strategy rather than training bespoke
neural operators per PDE family. Poseidon and DPOT are the cleanest primary-source
anchors for that architectural pivot.

---

## 2. Dataset counts (corrected, time-scoped, mismatch-aware)

### OQMD (Open Quantum Materials Database)

- **Current count:** 1,317,811 materials (OQMD homepage, [oqmd.org](https://oqmd.org/))
- **Confirmed by:** OPTIMADE provider dashboard (checked 2026-02-05)
- **Database version:** OQMD v1.7 (updated May 2025)

**Verification status:** CONFIRMED. Homepage and OPTIMADE dashboard agree on 1,317,811.

### ODAC25 (Open DAC 2025)

- **Canonical count (arXiv v2):** "nearly 60 million" DFT single-point calculations
  - Source: [arXiv 2508.03162v2](https://arxiv.org/abs/2508.03162v2) (revised 23 Sep 2025)
- **Landing-page mismatch:** FAIR Chemistry dataset page states "nearly 70 million"
  - arXiv v1 also used "nearly 70 million"; v2 revised downward to "nearly 60 million"
  - Landing page is non-canonical unless updated to match v2

**Verification status:** CONFIRMED. The v1-to-v2 revision from ~70M to ~60M is verified
via arXiv metadata. The landing page retains the stale v1 figure.

### Operational rule

For continuously updated datasets: treat (a) latest arXiv revision as canonical for
headline counts, and (b) dataset landing pages as potentially stale marketing/summary
text unless versioned.

---

## 3. PyTorch distributed training (FSDP2) — corrected timeline

### FSDP2 origin (timeline fix)

FSDP2 was introduced as a **prototype** feature in **PyTorch 2.4** (July 2024 release).
The prior draft incorrectly stated "new in 2.10."

- **Source:** [PyTorch 2.4 Release Blog](https://pytorch.org/blog/pytorch2-4/)
- **RFC:** [GitHub Issue #114299](https://github.com/pytorch/pytorch/issues/114299)

### Current API and semantics

`torch.distributed.fsdp.fully_shard` documentation defines FSDP2 as DTensor-based
per-parameter sharding. Key behavioral contract: DTensor conversion, gather/unshard
hooks, dim-0 chunking across data parallel workers.

- **Docs:** [fully_shard API](https://docs.pytorch.org/docs/stable/distributed.fsdp.fully_shard.html)

### Production signal

TorchTitan lists "FSDP2 with per-parameter sharding" as a key supported feature,
indicating this is the path PyTorch expects serious scaling users to take.

- **Source:** [pytorch/torchtitan](https://github.com/pytorch/torchtitan/blob/main/docs/fsdp.md)

**Verification status:** CONFIRMED. PyTorch 2.4 blog explicitly lists FSDP2 as prototype.
Current docs at PyTorch 2.10 show it as stable API.

---

## 4. Governance timeline (EU AI Act) — corrected wording

### What is safe to state

- The AI Act applies **progressively**; full roll-out foreseen by **2 Aug 2027**.
- **2 Feb 2025:** Prohibitions, definitions, AI literacy provisions applicable.
- **2 Aug 2025:** GPAI obligations and governance rules applicable.
- **2 Aug 2026:** Majority of rules come into force; enforcement starts. High-risk
  systems (Annex III), transparency requirements (Art. 50), innovation measures apply.
- **2 Aug 2027:** Extended transition for high-risk AI embedded in regulated products
  (Annex II). Legacy GPAI compliance deadline.

### Why this wording

The Commission's overview page says "fully applicable ... with some exceptions," which
is legally correct but easy for engineers to misinterpret as "everything applies then."
This memo adopts the clearer AI Act Service Desk timeline phrasing.

- **Source:** [AI Act Service Desk Timeline](https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act)
- **Also:** [artificialintelligenceact.eu/implementation-timeline](https://artificialintelligenceact.eu/implementation-timeline/)

**Verification status:** CONFIRMED. Dates cross-checked against multiple official EU
sources and independent compliance trackers. Progressive timeline is consistent.

---

## 5. Conformal prediction — corrected attribution

### 2014 (JRSS-B): conditional validity limits

Lei & Wasserman, "Distribution-free Prediction Bands for Non-parametric Regression,"
*Journal of the Royal Statistical Society Series B*, 76(1):71-96, 2014.

This is the correct anchor for: conditional coverage is not generally achievable in
finite samples without assumptions; marginal vs. conditional vs. local validity discussion.

- **Published:** [Oxford Academic](https://academic.oup.com/jrsssb/article-abstract/76/1/71/7075937)
- **arXiv:** [1203.5422](https://arxiv.org/abs/1203.5422)

### 2018 (JASA): regression predictive inference framework

Lei, G'Sell, Rinaldo, Tibshirani, Wasserman, "Distribution-Free Predictive Inference
for Regression," *Journal of the American Statistical Association*, 113(523):1094-1111, 2018.

This is the correct citation for the broader conformal framework and associated
methods/variants (full conformal, split conformal, jackknife).

- **Published:** [Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/01621459.2017.1307116)
- **arXiv:** [1604.04173](https://arxiv.org/abs/1604.04173)
- **Code:** [github.com/ryantibs/conformal](https://github.com/ryantibs/conformal)

### Safety-critical wording (corrected)

Conformal methods provide finite-sample marginal coverage under exchangeability; they
do **not** guarantee per-input conditional coverage absent strong assumptions.

**Verification status:** CONFIRMED. Both papers verified via publisher pages, arXiv, and
CMU author pages. The 2014 vs. 2018 distinction is clear and correctly attributed.

---

## 6. MFEM / extreme-scale finite elements — corrected hardware and award

### What happened (correctly framed)

- LLNL used **43,520 AMD Instinct MI300A APUs** on El Capitan (>46,000 APUs total in
  the system, >11 million CPU cores) to achieve **55.5 trillion degrees of freedom** in
  the offline phase of a tsunami "digital twin" workflow.
- The work won the **2025 ACM Gordon Bell Prize** (announced Nov 20, 2025 at SC25).

### Sources

- **LLNL announcement:** [llnl.gov/article/53636](https://www.llnl.gov/article/53636/llnl-ut-ucsd-win-gordon-bell-prize-exascale-tsunami-forecasting)
- **InsideHPC coverage:** [insidehpc.com](https://insidehpc.com/2025/11/llnl-ut-austin-and-ucsd-collaboration-on-tsunami-forecasting-wins-acm-gordon-bell-prize-at-sc25/)

### Terminology standard

Call them "MI300A APUs/accelerators." Avoid asserting "GPUs" as the precise product
class, even if some press uses "GPU" loosely. The MI300A is an Accelerated Processing
Unit combining CPU and GPU dies on a single package.

**Verification status:** CONFIRMED. LLNL press release and InsideHPC both say "MI300A
APUs," confirm 55.5T DoF, confirm Gordon Bell Prize winner (not just finalist).

---

## 7. OpenFOAM + Keysight/ESI — corrected acquisition timeline

### Financial reality

Keysight's investor release (Jan 10, 2024) states: after settlement-delivery on
**Jan 18, 2024**, Keysight holds **98.2%** of ESI Group shares, enabling squeeze-out
at EUR 155/share.

- **Source:** [Keysight investor release](https://investor.keysight.com/investor-news-and-events/financial-press-releases/press-release-details/2024/Keysight-Announces-Result-of-Cash-Tender-Offer-for-Shares-of-ESI-Group/default.aspx)

### Operational / branding narrative

OpenFOAM's v2506 release note says "since May 1st" the OpenFOAM team is part of
Keysight, describing integration activities. Development team is unchanged; open-source
philosophy and release schedule continue.

- **Source:** [OpenFOAM v2506 announcement](https://www.openfoam.com/news/main-news/openfoam-v2506)

### How to state it without contradiction

> "Keysight obtained controlling ownership of ESI by early 2024 (98.2% of shares,
> settlement Jan 18 2024). OpenFOAM's Keysight integration messaging became explicit
> in May 2025."

**Verification status:** CONFIRMED. Financial and operational dates are distinct and
now correctly separated.

---

## Provenance and methodology

Each claim in this memo was verified on 2026-02-15 against primary sources via web
search. The verification approach:

1. **Dataset counts:** Cross-referenced homepage, OPTIMADE dashboard, arXiv revisions
2. **Paper venues/claims:** Checked publisher proceedings pages, OpenReview, arXiv
3. **Timelines:** Cross-referenced official government/organizational pages
4. **Financial events:** Checked investor relations press releases
5. **Hardware terminology:** Checked LLNL and vendor press releases

### Known source disagreements (mismatch register)

| Topic | Source A | Source B | Resolution |
|-------|----------|----------|------------|
| ODAC25 count | arXiv v2: "nearly 60M" | FAIR landing page: "nearly 70M" | arXiv v2 is canonical |
| Keysight-ESI date | Finance: Jan 2024 | OpenFOAM comms: May 2025 | Both correct; different events |
| EU AI Act "fully applicable" | Commission overview | AI Act Service Desk | Service Desk timeline is clearer |

### Next step (recommended)

Turn these verified facts into a machine-checkable evidence appendix: a script that
snapshots key pages/DOIs + hashes + retrieval timestamps, so the unveiling deck can
say: "Every number is traceable; here is the provenance bundle."
