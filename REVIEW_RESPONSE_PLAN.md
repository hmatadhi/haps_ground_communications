# Fix plan: Dixit review comments on HAPS_SHORTENED_FINAL.tex

Status: planning only, no `.tex` edits applied. Each item below has a concrete fix;
items 9 and 10 need a decision from you before I touch anything, because both
affect numbers/claims that propagate elsewhere in the paper
(abstract, conclusion, tables — per the end-to-end consistency rule).

---

## 1. "Prof." in title / Sonali's name

`\author` line (L57): `Harsha Matadhikari, Prof.~Sonali Garg, Prof.~Abhishek Dixit`

Fix: drop both `Prof.~` tokens, and change `Sonali Garg` → `Sonali` everywhere the
name appears (author line, `\address[2]`, `\markboth` lines reference surname only
so unaffected). Mechanical, no side effects.

## 2. IITD affiliation

No text fix — this is a reminder for me to raise with you, not a paper edit.
Current `\address[1]` already lists "Indian Institute of Technology Delhi... ;
Principal Engineer, Nouveau Labs". **Reminder: confirm with Dixit whether IITD
can be listed as your affiliation before the next submission.**

## 3. Remove Part I/II/III divisions

The `\paperpart{...}` macro (defined L39-46, invoked 3×: L132 "Channel and
Attenuation Model", L344 "Baseline Association Policies", L362 "Learned
Association Policy") renders the "PART I/II/III" banners. Fix: delete the three
`\paperpart{...}` invocations. The macro definition can stay unused or be removed
too. The section numbering is untouched since `\paperpart` doesn't number sections,
only the banner. This is also where comment 4's merge will change section
boundaries anyway, so do both in the same pass.

## 4. Reduce to 6-7 sections

Currently 14 top-level `\section`: Introduction, Related Work, System Topology
and Channel Model, Atmospheric and Propagation Models, Multi-HAPS Interference...,
Simulation Results, Baseline Association Policies, Motivation for Learning,
LSTM Rain-Attenuation Forecaster, DQN Association Agent, DQN Results, Conclusion,
Abbreviations, References.

Proposed merge to 7 (References and the mandatory IEEE-style back matter don't
usually count against a journal's "section" limit, but I'd fold Abbreviations
away per item 6 anyway):

1. **Introduction** (unchanged)
2. **Related Work** (unchanged)
3. **Channel and Propagation Model** — merge "System Topology and Channel Model"
   + "Atmospheric and Propagation Models" (its two subsections become
   subsections here)
4. **Multi-HAPS Interference and Relay Path** — merge "Multi-HAPS Interference,
   SINR, and the Relay Path" + "Simulation Results" (results become subsections
   of this, since they're numeric characterization of the same model)
5. **Association Policies** — merge "Baseline Association Policies" +
   "Motivation for Learning" (motivation becomes a short intro paragraph or
   subsection of this section, not its own section)
6. **Learned Policy: LSTM + DQN** — merge "LSTM Rain-Attenuation Forecaster" +
   "DQN Association Agent" + "DQN Results" into one section with 3 subsections
7. **Discussion, Future Work, and Conclusion** — see item 7 below

This is a heading/restructuring pass (retitle `\section`→`\subsection` at merge
points, fix `\label`/`\ref` targets that assumed section-level labels — I'll need
to grep every `\S\ref{...}` and `Fig./Table` cross-reference after merging since
several sentences say "\S\ref{sec:results}" etc. and those labels must still
resolve to sensible subsection anchors).

## 5. Reduce references to ~20, favor post-2020

Current bibliography has 27 entries. Breakdown by date and removability:

**Foundational / hard to replace with newer work (recommend keep even if pre-2020):**
`itu_p838` (2005, the core P.838 rain model — the paper's central equation depends
on it), `mnih2015dqn` (2015, origin of DQN), `jain1984quantitative` (fairness index
origin), `goldsmith2005` (SINR linear-domain convention). These are method
citations, not "state of the art" citations — a reviewer complaint about recency
is usually about the latter, not the former.

**Pre-2020 and plausibly droppable or consolidatable:**
- `itu_m2106` (2012) — duplicate of `itu_m2101` (2017) for the same HAPS
  characteristics claim at L87; cite only `itu_m2101`.
- `itu_p835` (2017), `itu_p836` (2017) — check if actually cited/used in the final
  text (I didn't see `\cite{itu_p835}` or `\cite{itu_p836}` used in-text in the
  sections I read — if unused, delete outright).
- `itu_p837` (2017) — used (Delhi rain statistics, L197) — keep, it's load-bearing,
  recency doesn't apply to a statistics standard.
- `ecc_rec_04_05` — check if cited in text; if not, delete.
- `schulman2017ppo` (2017) — cited only to say "PPO was considered but DQN suits
  better" (L123); this is a throwaway comparison, could cite in one clause without
  a dedicated reference, or drop.
- `3gpp_ts36104` (2021, OK) vs `3gpp_ts38214` (2021) vs `3gpp_ts38821` (2022) —
  three different 3GPP TRs/TSs; check whether all three are actually load-bearing
  or if one subsumes another's purpose in-text.

**Two entries have literal unresolved TODOs and need fixing regardless of count:**
- `wrc19` (L177): ends with `[Verify resolution number and footnote wording
  against the Radio Regulations.]` — this bracket is a note-to-self left in the
  bibliography, not reviewer-facing text, but it's visible in the compiled
  reference list structure if not stripped, and more importantly the citation is
  *unverified*. Needs checking before submission regardless of the reference-count ask.
- `3gpp_ts38101_5` (L180): same pattern, `[Verify release number.]`.

**Recommended action:** drop `itu_m2106`, and the two `itu_p835`/`itu_p836`/`ecc_rec_04_05`
entries if grep confirms they're unused in-text, verify-and-fix the two `[Verify...]`
placeholders, and fold the PPO aside into prose without its own citation. That gets
to ~22-23 without removing anything load-bearing. Reaching exactly 20 likely means
cutting one of the three 3GPP standards or one of the two broad surveys
(`svistunov2025haps`, `bakambekova2024`) — I'd want your/Dixit's call on which,
since both surveys are doing "positioning" work in Related Work, not filler.

## 6. Remove separate Abbreviations section

`abbreviations.tex` has 23 entries (L549-551 of main file: `\section{Abbreviations}`
+ `\input{./abbreviations.tex}`). Fix: delete that `\section` and its `\input`, and
for each abbreviation, verify it's expanded at first use in running text. Quick
check against the current text: ABS, CDF, FDMA, GW, MLP, MVP, PDF, PL, RH, TDMA,
TD, UTD appear in the abbreviations list but I didn't see all of them used in the
sections I read — some may be leftovers from an earlier draft (table/figure
captions I haven't checked, or genuinely unused). Before deleting the section I'll
need to grep each abbreviation's usage sitewide to confirm first-use expansion
exists (e.g. "Deep Q-Network (DQN)" rather than bare "DQN") and add expansions
wherever missing — this is the real work here, the section deletion itself is trivial.

## 7. Shorten Conclusion; add Discussion and Future Work

Current `\section{Conclusion}` (L509-547) is doing three jobs: (a) summarizing
Backhaul/Service/Relay/Learned-association findings (L513-525), (b) a "Roadmap for
future investigations" with 3 numbered items and sub-bullets (L527-547) — this
*is* future work, just not labeled as its own section. Fix:

- New **`\section{Discussion and Future Work}`** before Conclusion, containing:
  - The existing "Roadmap" content (L527-547) moved here as "Future Work" subsection.
  - A new "Discussion" subsection that directly answers comment 10 (see below) —
    this is also where the honest DQN/LSTM framing belongs, not buried in DQN Results.
- New **`\section{Conclusion}`**, 2 paragraphs: paragraph 1 = channel-model
  findings (condense current Backhaul/Service/Relay bullets into prose, 3-4
  sentences), paragraph 2 = learned-policy finding + one-sentence pointer to the
  Discussion section for the "why DQN" nuance, rather than re-litigating it here.

## 8. Figure/table caption font size

Current table captions use `\captionof{table}` / `\caption{}` at default size,
but table *contents* are wrapped in `{\scriptsize ...}` (e.g. L142, L396) — the
*caption* text itself isn't explicitly sized down, so it may be rendering at the
body-text size while the table contents are `\scriptsize`, making captions look
oversized relative to their tables. IEEE Access standard is caption text in
`\footnotesize` (this is what `ieeeaccess.cls` / IEEEtran normally sets by
default for `\caption` — need to check whether `ieeeaccess.cls` already overrides
this or whether something in the preamble, e.g. `\setlength{\abovecaptionskip}`
block at L29-33, is interacting with caption font). Fix: audit every
`\caption{}`/`\captionof{...}` call (there are ~10) and the figures using
`\footnotesize` prefix inside `\centering` blocks (e.g. L269 already does this
for the relay-capacity table) — make that pattern consistent everywhere, and
remove any explicit font-size override larger than what `ieeeaccess.cls` defaults
to. This needs a compiled PDF comparison (you said you compile, not me) to confirm
visually before/after.

## 9. Table I gateway placement vs. 89.86° elevation — the real inconsistency

Confirmed and reproduced the reviewer's math:

- Table I (L147-151): HAPS at 20 km altitude, 3 nodes, **equilateral 65 km
  spacing**; Gateway at **"Centroid of HAPS triangle"**.
- Centroid of an equilateral triangle with side 65 km is at circumradius
  `65/√3 ≈ 37.5 km` from each vertex's ground projection (this exact number is
  used elsewhere in the paper for the UAV, L266: "circumradius $65/\sqrt{3}\approx37.5$km").
- At 20 km altitude and 37.5 km horizontal offset, elevation angle = arctan(20/37.5)
  **≈ 28.1°** — this is essentially the same geometry the paper already computes
  for the UAV feeder hop (**27.5°**, L259/266), because the UAV is *also* placed at
  that same centroid.
- But the backhaul-link text (L195, L197, L257) and the LSTM section (L381)
  assume the HAPS--Gateway link is **near-nadir, ≈89.86°** elevation — i.e., the
  gateway is directly below its serving HAPS, not at the triangle's centroid.

These two placements (centroid vs. near-nadir-under-one-HAPS) are mutually
exclusive for the same point. Table I currently asserts the gateway is at the
centroid; the entire backhaul rain/SINR/margin analysis (the ≈19 dB rain loss,
≈38 dB clear-sky SINR, ≈18.6 dB margin, and the LSTM's training target) assumes
near-nadir. **This is a real bug, not just a clarity issue** — Dixit is right.

**Two ways to resolve it — I need your call before editing anything, since each
has different downstream cost:**

- **Option A (small fix, no recompute):** Table I's gateway row is simply wrong/
  misleadingly worded. In a real deployment the gateway's ground site is chosen
  independently of the UAV relay's position — it's sited to minimize backhaul
  slant distance to its primary serving HAPS, which is a *different* engineering
  decision from where the UAV relay sits (chosen instead for coverage centrality,
  per L266). Fix: change Table I's Gateway row to "Near-nadir under serving HAPS
  (89.86° elevation)" and add one clarifying sentence in §System Topology
  distinguishing "gateway siting (minimizes backhaul distance)" from "UAV siting
  (maximizes feeder-hop symmetry via centroid placement)" as two independent
  choices that happen to both be near the same HAPS cluster but are not the same
  point. **No numbers change** — all existing rain/SINR/margin values stay valid
  because they already assumed near-nadir. I recommend this option: it's the
  smaller, lower-risk fix and the backhaul numbers are already self-consistent
  internally, only Table I's label was wrong.
- **Option B (recompute):** Take Table I literally — gateway really is at the
  centroid, elevation ≈27.5°, same as the UAV feeder hop. Then the backhaul rain
  coefficients (`k`, `α` in Eq. rain_spec_atten, L192), effective slant length
  `L_eff`, the ≈19 dB rain loss, the ≈38 dB clear-sky SINR, the ≈18.6 dB margin
  (L199-201), the near-nadir claim in Related Work (L119) and System Topology
  (L165), and the LSTM's "89.86° elevation" training-target description (L381)
  all need to be recomputed at ≈27.5° and re-propagated through every place that
  cites those numbers (abstract doesn't cite the exact dB figures so is likely
  unaffected, but the Backhaul paragraph in Conclusion, L515, restates them and
  would need updating too). This means re-running whatever generator script
  produced those backhaul figures (likely in `src/`) with the corrected elevation.
  Only worth doing if the backhaul-at-the-gateway's-actual-site is genuinely meant
  to be centroid-colocated in your model (i.e., gateway and UAV are the same
  ground facility) — if that's not physically intended, Option A is correct.

I'd ask Dixit/you to confirm which is physically intended, but my read of the
paper's own internal logic (UAV placement is justified by a *different*
rationale — coverage centrality for relay purposes — than gateway placement,
which should minimize backhaul path loss) is that **Option A is the actual bug
fix** and Option B would be "fixing" something that was never meant to be true.

## 10. Unclear advantage of DQN/LSTM (Table IV)

Two separate issues bundled in this comment:

**(a) Abstract overclaims relative to what Table IV / Fig. paired-forest actually show.**
Abstract (L72) says: *"The learned policy matches both rule-based baselines on
reward while uniquely retaining and using the relay path..."* But the paired
significance tests (L505) show DQN is **significantly worse** than both baselines
on reward (p<0.0001, 0/10 seeds favoring DQN), worse on Jain fairness (p=0.0003
and p=0.0099), and worse on outage (p=0.0002 and p<0.0001) — it only *ties* on
battery SoC (p=0.19, p=0.09). "Matches on reward" is not an accurate summary of
that result and should be fixed regardless of comment 10 — this is an end-to-end
consistency issue (abstract vs. own Table IV/Fig. 14) independent of how we
answer Dixit's deeper "what's the advantage" question. Fix: reword the abstract's
closing sentence to say the learned policy is *statistically close but not
better* on reward/fairness/outage, and its actual advantage is operating under
realistic partial information (no instantaneous global SINR/capacity knowledge)
while still retaining the ability to invoke the relay selectively — i.e., state
the real finding instead of "matches."

**(b) The deeper question — is there an actual advantage, stated plainly.**
The paper's existing answer (L482-488, and the forecast-ablation paragraph
L507) is scattered across DQN Results rather than argued head-on, which is why
Dixit "got lost." The honest advantage, as the paper's own numbers support, is
narrower than originally framed: Max-SINR and Max-throughput are **not
deployable baselines** — they require instantaneous, perfect knowledge of SINR
to all 3 HAPS (max-SINR) or capacity of all 6 options including the relay hop
(max-throughput) *before* making each hourly decision, which assumes exactly the
kind of real-time, zero-latency global measurement a real HAPS network doesn't
have. The DQN gets within ~1 dB of reward and ~1 outage/50 of these unrealizable
upper bounds using only locally available state (SINR to platforms already in
range, forecast, battery) — so the finding is "near-oracle performance without
oracle information," not "better than the alternatives." Separately and
honestly: the LSTM rain forecast itself provides **no measurable benefit** to the
DQN's performance in the current single-UAV, single-gateway setup (the
lstm/none/oracle ablation at L507 — statistically indistinguishable), because
both link types are already well-margined against rain at this scale. That's a
negative result worth stating as a negative result, not minimizing.

**Recommended fix:** Add the "Discussion" subsection called for in item 7, with
an explicit paragraph structured as: (i) restate the comparison honestly —
near-oracle, not superior; (ii) explain *why* that's still the paper's
contribution — it's the only policy of the four that is actually implementable
without global instantaneous measurement, and it uniquely uses the relay
selectively for near-outage users; (iii) state the rain-forecast null result
plainly as a finding about this model's scale (margin is large enough that
forecasting adds nothing yet), not a failure, and point to the fleet-scale future
work (§Future Work) as where that calculus might change. Then fix the abstract
per (a) so it's consistent with this reframed claim.

---

## Suggested order of operations (when you're ready to apply)

1. Items 1, 2 (reminder only), 6 — mechanical, no numeric dependencies.
2. Item 9 Option A — Table I correction + one clarifying sentence (confirm Option
   A vs B with Dixit first).
3. Item 10(a) — fix abstract wording to match Table IV (depends on nothing else,
   should happen regardless of how 10(b) is resolved).
4. Item 10(b) + Item 7 — write the new Discussion and Future Work section, shrink
   Conclusion to 2 paragraphs.
5. Item 3 + Item 4 — remove Part dividers and merge sections into 6-7 (do these
   together since merging changes where the Part banners would have sat anyway).
6. Item 5 — bibliography trim (needs the in-text `\cite` grep to confirm which
   entries are actually unused before deleting).
7. Item 8 — caption font audit, verify by compiling.

Items 1-6 and 8 are low-risk mechanical fixes. Items 9 and 10 are the ones where
I want your (and possibly Dixit's) explicit sign-off on the approach before
editing, since both touch claims that cascade into the abstract and conclusion.
