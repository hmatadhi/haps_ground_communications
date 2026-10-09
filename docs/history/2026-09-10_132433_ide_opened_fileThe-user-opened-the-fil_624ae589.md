# Claude Code Session

| Field | Value |
|---|---|
| **Project** | `c:\Github-haps-ground-communications` |
| **Session ID** | `624ae589-10a3-4b9e-ad1f-e8ccf4b640e0` |
| **Working Dir** | `c:\Github\haps_ground_communications` |
| **Started** | 9/10/2026, 1:24:33 PM |
| **Last Updated** | 9/10/2026, 2:47:04 PM |
| **Messages** | 50 |

---

## User <sup>9/10/2026, 1:24:33 PM</sup>

<ide_opened_file>The user opened the file c:\Github\haps_ground_communications\HAPS_AI_HW_ChannelModel.tex in the IDE. This may or may not be related to the current task.</ide_opened_file>

> *[Image]*

Remove the white space between paragraphs and pictures in this page.
C:\Github\haps_ground_communications\HAPS_AI_HW_ChannelModel.tex


---

## Assistant <sup>9/10/2026, 1:24:36 PM</sup>


---

## Assistant <sup>9/10/2026, 1:24:38 PM</sup>

<details>
<summary>Tool: <code>Grep</code></summary>

```json
{
  "pattern": "DQN Results and Validation Against the Closed-Form",
  "path": "c:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "output_mode": "content",
  "-n": true
}
```

</details>


---

## User <sup>9/10/2026, 1:24:38 PM</sup>

<details>
<summary>Tool Result</summary>

```
1027:\subsection{DQN Results and Validation Against the Closed-Form Baseline}
```

</details>


---

## Assistant <sup>9/10/2026, 1:24:41 PM</sup>

<details>
<summary>Tool: <code>Read</code></summary>

```json
{
  "file_path": "c:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "offset": 960,
  "limit": 100
}
```

</details>


---

## User <sup>9/10/2026, 1:24:41 PM</sup>

<details>
<summary>Tool Result</summary>

```
960	\textbf{Error 5:} Reward broadcast to all $N$ users identically (the fully-aggregated
961	network reward $R(\mathbf{a})$ given to every user's transition, regardless of that
962	user's own action). With $N=50$ simultaneously-acting users, any single user's choice
963	moves $R(\mathbf{a})$ by only a small fraction of its value, so the DQN cannot tell
964	which action caused the change -- training collapsed to a constant always-pick-HAPS-1
965	policy (identical evaluation reward/fairness/outage across 200+ consecutive training
966	episodes; verified by inspecting the learned policy's action distribution directly).
967	\textbf{Fix:} Decompose the additive components of $R(\mathbf{a})$ -- $L_{\text{agg}}$
968	and the outage penalties are literally sums (resp. fractions) over users -- into a
969	per-user share, so each user is credited with its own throughput/outage contribution.
970	$J_{\text{fair}}$ and $P_{\text{eng}}$ are genuinely network-level and remain a shared
971	term. This do
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 1:24:45 PM</sup>


---

## Assistant <sup>9/10/2026, 1:24:46 PM</sup>

<details>
<summary>Tool: <code>Read</code></summary>

```json
{
  "file_path": "c:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "offset": 1059,
  "limit": 70
}
```

</details>


---

## User <sup>9/10/2026, 1:24:46 PM</sup>

<details>
<summary>Tool Result</summary>

```
1059	
1060	Refer to Table~\ref{tab:phase2-results} and Figure~\ref{fig:baseline-comparison} for a 
1061	comparison of the three policies. Evidently the results show that Max-SINR is the 
1062	best-performing policy for this configuration. It achieves the highest evaluation 
1063	reward (≈−20), the highest Jain fairness (≈0.70), and by far the lowest outage (≈1%),
1064	 while maintaining essentially the same mean battery SoC (≈61%) as DQN and random.
1065	However DQN performs substantially better than random, with higher reward (≈−34),
1066	 better fairness (≈0.61), and lower outage (≈10%), but remains consistently behind Max-SINR.
1067	The error bars indicate variability around the reported mean values. 
1068	Closing this gap through extended training, improved exploration/reward shaping, or 
1069	harder scenarios remains future work.
1070	
1071	\begin{figure}[t]
1072	\centering
1073	\includegraphics[width=\linewidth]{./figures/8_dqn_association_convergence.png}
1074	\caption{DQN train
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 1:26:06 PM</sup>


---

## Assistant <sup>9/10/2026, 1:26:07 PM</sup>

<details>
<summary>Tool: <code>Grep</code></summary>

```json
{
  "pattern": "flushbottom|raggedbottom|documentclass",
  "path": "c:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "output_mode": "content",
  "-n": true
}
```

</details>


---

## User <sup>9/10/2026, 1:26:07 PM</sup>

<details>
<summary>Tool Result</summary>

```
1:\documentclass[conference]{IEEEtran}
```

</details>


---

## Assistant <sup>9/10/2026, 1:26:14 PM</sup>


---

## Assistant <sup>9/10/2026, 1:26:14 PM</sup>

<details>
<summary>Tool: <code>Bash</code></summary>

```json
{
  "command": "which pdflatex latexmk 2>&1; pdflatex --version 2>&1 | head -3",
  "description": "Check if pdflatex is available"
}
```

</details>


---

## User <sup>9/10/2026, 1:29:10 PM</sup>

<details>
<summary>Tool Result</summary>

```
/c/Users/harsh/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex
/c/Users/harsh/AppData/Local/Programs/MiKTeX/miktex/bin/x64/latexmk
MiKTeX-pdfTeX 4.26 (MiKTeX 26.2)
© 1982 D. E. Knuth, © 1996-2026 Hàn Thế Thành
TeX is a trademark of the American Mathematical Society.
```

</details>


---

## Assistant <sup>9/10/2026, 1:29:12 PM</sup>

Good, pdflatex is available. Let me compile the current file to confirm the page layout and reproduce the whitespace issue before making changes.


---

## Assistant <sup>9/10/2026, 1:29:14 PM</sup>

<details>
<summary>Tool: <code>Bash</code></summary>

```json
{
  "command": "pdflatex -interaction=nonstopmode HAPS_AI_HW_ChannelModel.tex > /tmp_build1.log 2>&1; tail -40 /tmp_build1.log",
  "description": "Compile the LaTeX document to reproduce current state",
  "timeout": 120000
}
```

</details>


---

## User <sup>9/10/2026, 1:29:25 PM</sup>

<details>
<summary>Tool Result</summary>

```
The user doesn't want to proceed with this tool use. The tool use was rejected (eg. if it was a file edit, the new_string was NOT written to the file). The user provided the following reason for the rejection:  i will compile
```

</details>


---

## Assistant <sup>9/10/2026, 1:29:57 PM</sup>


---

## Assistant <sup>9/10/2026, 1:29:57 PM</sup>

<details>
<summary>Tool: <code>Grep</code></summary>

```json
{
  "pattern": "Float|float|Overfull|Underfull",
  "path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.log",
  "output_mode": "content",
  "-n": true
}
```

</details>


---

## User <sup>9/10/2026, 1:29:57 PM</sup>

<details>
<summary>Tool Result</summary>

```
361:\c@continuedfloat=\count316
611:Underfull \hbox (badness 10000) in paragraph at lines 386--388
616:Underfull \hbox (badness 4181) in paragraph at lines 386--388
627:LaTeX Warning: `!h' float specifier changed to `!ht'.
630:Underfull \hbox (badness 10000) in paragraph at lines 429--430
636:Underfull \hbox (badness 10000) in paragraph at lines 429--430
641:Underfull \hbox (badness 3209) in paragraph at lines 429--430
670:Underfull \hbox (badness 1365) in paragraph at lines 16--16
675:LaTeX Warning: `!h' float specifier changed to `!ht'.
679:LaTeX Warning: `!h' float specifier changed to `!ht'.
690:LaTeX Warning: `!h' float specifier changed to `!ht'.
693:Underfull \vbox (badness 1314) has occurred while \output is active []
705:LaTeX Warning: `!h' float specifier changed to `!ht'.
722:LaTeX Warning: `!h' float specifier changed to `!ht'.
789:Underfull \hbox (badness 1838) in paragraph at lines 855--856
795:Underfull \hbox (badness 10000) in paragraph at lines 857--858
801:Underfull \
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 1:30:02 PM</sup>


---

## Assistant <sup>9/10/2026, 1:30:03 PM</sup>

<details>
<summary>Tool: <code>Read</code></summary>

```json
{
  "file_path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.log",
  "offset": 955,
  "limit": 40
}
```

</details>


---

## User <sup>9/10/2026, 1:30:03 PM</sup>

<details>
<summary>Tool Result</summary>

```
955	<./figures/8_dqn_association_convergence.png, id=520, 505.89pt x 433.62pt>
956	File: ./figures/8_dqn_association_convergence.png Graphic file (type png)
957	<use ./figures/8_dqn_association_convergence.png>
958	Package pdftex.def Info: ./figures/8_dqn_association_convergence.png  used on i
959	nput line 1073.
960	(pdftex.def)             Requested size: 252.0pt x 216.00224pt.
961	<./figures/9_baseline_comparison.png, id=521, 505.89pt x 433.62pt>
962	File: ./figures/9_baseline_comparison.png Graphic file (type png)
963	<use ./figures/9_baseline_comparison.png>
964	Package pdftex.def Info: ./figures/9_baseline_comparison.png  used on input lin
965	e 1081.
966	(pdftex.def)             Requested size: 252.0pt x 216.00224pt.
967	(abbreviations.tex)
968	Overfull \hbox (19.23637pt too wide) in paragraph at lines 1--1092
969	[][]
970	 []
971	
972	
973	Underfull \hbox (badness 10000) in paragraph at lines 1--1092
974	
975	 []
976	
977	
978	Underfull \vbox (badness 10000) has occurred while 
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 1:30:10 PM</sup>


---

## Assistant <sup>9/10/2026, 1:30:10 PM</sup>

<details>
<summary>Tool: <code>Read</code></summary>

```json
{
  "file_path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "offset": 1,
  "limit": 40
}
```

</details>


---

## User <sup>9/10/2026, 1:30:10 PM</sup>

<details>
<summary>Tool Result</summary>

```
1	\documentclass[conference]{IEEEtran}
2	\IEEEoverridecommandlockouts
3	
4	\usepackage{amsmath,amssymb,amsfonts}
5	\usepackage{graphicx}
6	\usepackage{xcolor}
7	\usepackage{listings}
8	\usepackage{url}
9	\usepackage{tabularx}
10	\usepackage{booktabs}
11	\usepackage{placeins}
12	\usepackage{cite}
13	\usepackage{subcaption}
14	\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue,bookmarksnumbered]{hyperref}
15	
16	\graphicspath{{figures/}{./}}
17	\setlength{\abovecaptionskip}{8pt plus 1pt minus 1pt}
18	\setlength{\belowcaptionskip}{4pt plus 1pt minus 1pt}
19	\setlength{\textfloatsep}{8pt plus 1pt minus 1pt}
20	\setlength{\floatsep}{6pt plus 1pt minus 1pt}
21	\setlength{\intextsep}{6pt plus 1pt minus 1pt}
22	\setlength{\parskip}{0pt}
23	\setlength{\parsep}{0pt}
24	\setlength{\topsep}{2pt}
25	\setlength{\itemsep}{2pt}
26	
27	% ---- syntax-highlighted Python listing style (pdflatex-safe, no minted) ----
28	\definecolor{codegreen}{rgb}{0.00,0.55,0.20}
29	\definecolor{codeg
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 1:30:15 PM</sup>

I've confirmed the cause from the build log: page 13 (the page shown) has two "Underfull \vbox (badness 10000) has occurred while \output is active" warnings — LaTeX's `\flushbottom` mode (IEEEtran's default) is stretching both columns to force them to reach the bottom margin, since this page is mostly floats with little text. That stretch is exactly the visible gap between the paragraphs and the table/figures. The standard fix is to switch to `\raggedbottom`, letting columns end early instead of being artificially stretched.


---

## Assistant <sup>9/10/2026, 1:30:16 PM</sup>

<details>
<summary>Tool: <code>Edit</code></summary>

```json
{
  "replace_all": false,
  "file_path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "old_string": "\\setlength{\\topsep}{2pt}\n\\setlength{\\itemsep}{2pt}",
  "new_string": "\\setlength{\\topsep}{2pt}\n\\setlength{\\itemsep}{2pt}\n\\raggedbottom"
}
```

</details>


---

## User <sup>9/10/2026, 1:30:18 PM</sup>

<details>
<summary>Tool Result</summary>

```
The file C:\Github\haps_ground_communications\HAPS_AI_HW_ChannelModel.tex has been updated successfully. (file state is current in your context — no need to Read it back)
```

</details>


---

## Assistant <sup>9/10/2026, 1:30:21 PM</sup>


---

## Assistant <sup>9/10/2026, 1:30:24 PM</sup>

Added `\raggedbottom` to the preamble ([HAPS_AI_HW_ChannelModel.tex:26](HAPS_AI_HW_ChannelModel.tex#L26)). This disables LaTeX's default `\flushbottom` column-stretching (IEEEtran's default), which was the confirmed cause per the log — page 13 had two "Underfull vbox, badness 10000" warnings from LaTeX stretching both sparse columns to force-fill the page. With `\raggedbottom`, columns will end naturally instead of being padded with rubber whitespace.

Go ahead and recompile to confirm the gaps on that page are gone — this is a document-wide setting, so worth a quick scan of other pages too in case any column-height differences look different than before (should generally look better, not worse).


---

## User <sup>9/10/2026, 1:38:44 PM</sup>

DoneThanks reporting to Sonali. COnfirm if the message is good.
Thanks for waiting for me and allowing some extra days, last week was very hectic for me at office and personal front.

I am submitting the updated report with DQN based implementation with two baseines, 1) max-SINR 2) randomised weather inputs fed to the equation and averaged. Observation is max-SINR performance always was better than max-SINR. But it is theoretical and not practical. DQN is practically better alternative. It can be further improved with LSTM predictions.


---

## Assistant <sup>9/10/2026, 1:38:54 PM</sup>


---

## Assistant <sup>9/10/2026, 1:38:54 PM</sup>

Let me check the baseline setup section in the report to verify the technical claims before confirming the message.


---

## Assistant <sup>9/10/2026, 1:38:55 PM</sup>

<details>
<summary>Tool: <code>Grep</code></summary>

```json
{
  "pattern": "assoc-baseline-setup|Random baseline|Max-SINR",
  "path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "output_mode": "content",
  "-n": true
}
```

</details>


---

## User <sup>9/10/2026, 1:38:55 PM</sup>

<details>
<summary>Tool Result</summary>

```
366:\label{sec:assoc-baseline-setup}
387:  \item \textbf{Max-SINR}: each user always associates to $\arg\max_p \text{SINR}_{k,p}$
797:\subsection{IV.D: Multi-HAPS Association Baseline Results (Random vs.\ Max-SINR)}
800:Using the setup of Section~\ref{sec:assoc-baseline-setup}, this measures the two
815:Max-SINR & $\mathbf{0.700\pm0.027}$ & $\mathbf{1.0\pm0.9}$ & $\mathbf{76.18\pm3.57}$ \\
1032:In comparison to baseline setup (Section~\ref{sec:assoc-baseline-setup}) that evaluates
1033:closed-form Random/Max-SINR baseline the results of which are summarized in
1054:Max-SINR (no DRL) & $\mathbf{-19.3\pm17.5}$ & $\mathbf{0.700\pm0.027}$ & $\mathbf{1.0\pm0.9}$ & $\mathbf{76.18\pm3.57}$ \\
1062:comparison of the three policies. Evidently the results show that Max-SINR is the 
1067: better fairness (≈0.61), and lower outage (≈10%), but remains consistently behind Max-SINR.
```

</details>


---

## Assistant <sup>9/10/2026, 1:38:59 PM</sup>

<details>
<summary>Tool: <code>Read</code></summary>

```json
{
  "file_path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "offset": 366,
  "limit": 40
}
```

</details>


---

## User <sup>9/10/2026, 1:38:59 PM</sup>

<details>
<summary>Tool Result</summary>

```
366	\label{sec:assoc-baseline-setup}
367	
368	Building on the 3-HAPS constellation (Table~\ref{tab:config}) and the SINR model of
369	Sections~III.A--III.C, this section defines a per-user association experiment: each
370	of $N=50$ users, once per simulated hour, observes its SINR to each of the 3 HAPS
371	(dB, Eq.~\eqref{eq:sinr}), its horizontal distance to each (km), each HAPS's battery
372	state of charge (\%), and the current weather (rain rate, visibility, hour of day).
373	One episode is one simulated day (24 hourly steps). Per episode, user positions and
374	each HAPS's initial battery SoC ($\mathcal{U}(30,100)\,\%$) are drawn once and held
375	fixed; weather is drawn once per episode (\texttt{WeatherScenarioGenerator},
376	\texttt{random\_mix} mode). Each HAPS's battery is charged by a fixed diurnal solar
377	profile and discharged by a constant platform/feeder draw plus its currently-associated
378	users' share of load ($P_{k,\text{user}}=1$~W per user, ASSUMED); the solar/pl
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 1:39:09 PM</sup>


---

## Assistant <sup>9/10/2026, 1:39:15 PM</sup>

A few issues worth fixing before sending, since this is reporting results to your supervisor:

**1. Self-referential error (the important one):** "max-SINR performance always was better than max-SINR" — compares max-SINR to itself. Based on your Table VI results (Random: reward −82.2, Max-SINR: −19.3, DQN: −34.1), you mean **max-SINR was always better than DQN** (and Random).

**2. Baseline #2 description doesn't match your report:** Your tex file defines the two closed-form baselines as:
- **Random** — uniform-random platform choice each hour (sanity floor)
- **Max-SINR** — always picks argmax SINR platform

"Randomised weather inputs fed to the equation and averaged" isn't one of the two baselines — weather is randomized per episode for *all* policies (drawn once per episode, evaluated over 50 held-out episodes, reported as mean±std). If you meant the Random policy, say "Random (uniform-random platform association)" rather than describing it as a weather-averaging method — as written it will confuse a reader who checks the report.

**3. Typo:** "baseines" → "baselines"

**4. Minor grammar:** "hectic for me at office and personal front" → "hectic for me on both the office and personal fronts"

Suggested rewrite:

> Thanks for waiting for me and allowing some extra days — last week was very hectic for me on both the office and personal fronts.
>
> I am submitting the updated report with a DQN-based implementation compared against two closed-form baselines: 1) Max-SINR (always associates to the highest-SINR platform) and 2) Random (uniform-random platform choice). Observation: Max-SINR performance was always better than DQN. However, Max-SINR is theoretical/idealized and not practical (no memory of battery or fairness state), whereas DQN is a more practical alternative. It can be further improved with LSTM-based predictions.

Want me to adjust tone or shorten it further?


---

## User <sup>9/10/2026, 2:44:10 PM</sup>

Max-SINR is not practical because we need to continuously have a reserved receiver trying to measure SINR of all three HAPS flows, right?


---

## Assistant <sup>9/10/2026, 2:44:31 PM</sup>


---

## Assistant <sup>9/10/2026, 2:44:36 PM</sup>

Yes, that's the core reason — Max-SINR assumes the user always has instantaneous SINR readings for *all* candidate platforms, not just the one it's currently associated with. In practice that means either extra RF chains monitoring all three HAPS reference signals simultaneously, or time-multiplexed scanning (measurement gaps) that interrupt service — both cost power, add latency, and add signaling overhead. It's the classic "genie-aided" assumption in handover/association literature.

Worth adding one more reason, since it's explicitly called out in your own report ([HAPS_AI_HW_ChannelModel.tex:387-388](HAPS_AI_HW_ChannelModel.tex#L387-L388)): Max-SINR is also *myopic* — "no memory of battery or fairness state." It always routes users to the strongest platform regardless of that HAPS's battery SoC or existing load, so it can overload/drain the best-SINR platform over time. That's arguably the bigger practical drawback for a real deployment, not just the measurement overhead.

So a more complete line for Sonali would be something like: "Max-SINR is impractical because it requires continuously measuring SINR to all three HAPS (extra hardware/scanning overhead), and it's myopic — it ignores battery and fairness state, so it can overload the best platform rather than balancing load."


---

## User <sup>9/10/2026, 2:46:21 PM</sup>

We can addi it when she submits the review.  How do the current implementations if any do the selection


---

## Assistant <sup>9/10/2026, 2:46:41 PM</sup>


---

## Assistant <sup>9/10/2026, 2:46:43 PM</sup>

<details>
<summary>Tool: <code>Grep</code></summary>

```json
{
  "pattern": "handover|RSRP|RSRQ|3GPP|measurement gap|NTN|association",
  "path": "C:\\Github\\haps_ground_communications\\HAPS_AI_HW_ChannelModel.tex",
  "output_mode": "content",
  "-n": true,
  "-i": true
}
```

</details>


---

## User <sup>9/10/2026, 2:46:43 PM</sup>

<details>
<summary>Tool Result</summary>

```
89:   Feeder Links operate in the 38.0–39.5 GHz millimeter-wave band allocated to HAPS by ITU-R M.2101. This link provides high-capacity backhaul between the Ground Gateway (GW) and the aircraft, standardized by 3GPP NTN~\cite{3gpp_ts38821}.
91:  \item { Service link:  HAPS to User, f = 2.1 -- 2.2 GHz (S-band)~\cite{3gpp_ts38821}} \\
92: Service links operate in the 2 GHz FDD band (3GPP Band 1/3). This link is designed for connectivity to  user equipment, ensuring accessibility without
308:Service and relay links operate at 2--2.2 GHz (S-band per 3GPP TS 38.821), connecting ground users either directly to HAPS (service link, high elevation angle) or via UAV relays at 300 m altitude (relay link). Unlike the 38 GHz feeder link, the 2 GHz S-band is resilient to atmospheric effects (fog, rain, gas absorption all negligible per ITU-R P.618) but highly sensitive to building blockage. This section models LoS probability, path loss, and multi-node interference.
365:\subsection{III.D: Multi-HAP
...(truncated)
```

</details>


---

## Assistant <sup>9/10/2026, 2:46:56 PM</sup>


---

## Assistant <sup>9/10/2026, 2:47:04 PM</sup>

Real systems don't do the idealized "continuous argmax-SINR over all platforms" — they use a much cheaper, coarser approximation. Since your own report already cites 3GPP TS 38.821 (NTN standard, [HAPS_AI_HW_ChannelModel.tex:89](HAPS_AI_HW_ChannelModel.tex#L89)), this maps directly:

1. **Periodic, not continuous, measurement of serving link only.** The UE regularly measures RSRP/RSRQ of its *current* serving cell/platform using broadcast reference signals. It does **not** continuously measure all neighbors in parallel.

2. **Event-triggered neighbor scanning.** Only when the serving link degrades past a threshold does the UE get scheduled measurement gaps to briefly retune and sample neighbor platforms (3GPP measurement events, e.g., A3/A5-style triggers). This is exactly the "reserved receiver time" cost you flagged — it exists, but it's used sparingly, not continuously.

3. **Hysteresis + time-to-trigger.** A neighbor must beat the serving platform by a margin *and* stay better for a sustained duration before handover fires — this avoids the ping-ponging a naive per-hour argmax would cause.

4. **Ephemeris/geometry-assisted scheduling (NTN-specific).** Since HAPS/satellite trajectories are known in advance, NTN standards let the network pre-schedule handovers from known position/elevation-angle predictions rather than reacting to live measurements — cutting the sensing burden further versus terrestrial cellular.

5. **Network-assisted, load-aware decisions.** The network combines the (sparse) measurement reports with cell/platform load and capacity when deciding handover — it's not pure signal-strength-only, unlike your Max-SINR baseline.

So the honest framing for Sonali: real deployments approximate Max-SINR with a **periodic, event-triggered, hysteresis-damped, load-aware** version — never the instantaneous full-SINR, load-blind argmax your closed-form baseline computes. That's a good practicality contrast to lead into why a learned (DQN) policy, which implicitly folds in battery/load state from its input features, is closer to how real systems actually behave.


---
