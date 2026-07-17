# Draft: outcome-measurement methodology (for Ch. 3, with Ch. 6 notes)

_Paste-ready draft, 12 Jul 2026. Written to match exactly what `apps/api/app/services/outcome_engine.py` implements on branch `feat/plan-strategy-2026-07` (commits 4c068f9 + b7e8511) — the dual-use requirement from the Jul-2026 strategy plan (W4): the thesis chapter and the shipped measurement design must be the same design. Verify citation details before submission._

## 3.x Quasi-experimental outcome scoring: interrupted time series

Whether a remediation action *worked* cannot, in a production feedback system, be established by a randomized experiment: the action is applied to every affected customer at once, and withholding a fix from a control group is neither ethical nor commercially acceptable. Naïve before/after deltas, however, are weak evidence — they confound the intervention with trends and seasonality, and field evidence shows well-intentioned recovery actions can have null or even negative effects (Halperin et al., 2022, on Uber's apology experiments), which is precisely why measurement must be default-on rather than opt-in. CLARA therefore scores outcomes with an **interrupted time series (ITS) design using segmented regression** (Wagner et al., 2002; Bernal et al., 2017) — the standard quasi-experimental design when an intervention has a known onset date and no concurrent control is available.

**Model.** For a problem theme with journey/stage-scoped daily signal counts $y_t$ (signals per complete UTC day), with the action executed at day $t_0$:

$$y_t = \beta_0 + \beta_1 t + \beta_2\,\text{post}_t + \beta_3\,(t - t_0)\,\text{post}_t + \varepsilon_t$$

where $\text{post}_t = \mathbb{1}[t \ge t_0]$. $\beta_2$ estimates the immediate **level change**, $\beta_3$ the **slope change**. The reported effect is the model-implied difference at the end of the observation window between the fitted post-intervention trend and the pre-intervention counterfactual, $\hat\Delta = \beta_2 + h\beta_3$ with $h$ the horizon in days, with a 95% confidence interval from $\widehat{\text{Var}}(\beta_2 + h\beta_3) = \sigma^2\!\left[(X'X)^{-1}_{22} + h^2 (X'X)^{-1}_{33} + 2h (X'X)^{-1}_{23}\right]$ and Student-$t$ critical values at $n-4$ degrees of freedom. The estimator is closed-form OLS (normal equations, Gauss–Jordan with partial pivoting), implemented dependency-free in ~60 lines.

**Series construction (bias controls).** Three deliberate rules, each of which measurably biased the estimate when omitted:
1. **Complete UTC days only.** The bucket for the read-time day is a partial observation; entering it at full-day scale drags the endpoint of the fit — Monte-Carlo simulation on a no-effect series (Poisson(10) noise) showed a spurious negative point effect in ~66% of mid-day reads and false CI exclusion of zero in 5–7.5% of reads versus the nominal 2.5%.
2. **The execution day is excluded** from the fit: it mixes pre- and post-intervention exposure, and assigning it to the post segment understates $\beta_2$ and manufactures a spurious $\beta_3$.
3. **No fabricated history.** The pre-window (up to 28 days before execution) is truncated at the first observed signal; days before data existed are not counted as zeros.

**Honesty rules.** With fewer than 10 pre-intervention or 5 post-intervention daily buckets, the system refuses to fit and reports a labelled plain difference of means ("insufficient data for ITS") with **no confidence interval** — an underpowered regression dressed up with a CI would be less honest than a labelled delta. Simulated data is structurally quarantined: outcome series derive exclusively from raw ingested signals (`real_data_source` discipline), and the simulation harness cannot write measurements.

**Outcome contracts.** The measurement is contracted *before* acting: at approval time the system proposes — applied by default, editable, declinable — a contract with baseline = the trailing signal rate over the observed span (capped at 28 days; dividing by a fixed window would dilute young workspaces' baselines by up to 4×), a 30-day measurement window with a T+7 early read, and a success threshold of a 50% rate reduction. Scheduled re-measurement runs via pg_cron (or an in-process fallback loop) every 15 minutes over due checkpoints.

### Notes for Ch. 6 (limitations / future work)
- OLS standard errors assume serially uncorrelated residuals; daily rates are plausibly autocorrelated. Newey–West (HAC) errors are the designated upgrade path (noted in-code); the current CIs should be read as approximate.
- Counts are fitted by OLS on rates rather than a Poisson/negative-binomial GLM — adequate at the observed volumes, misspecified at very low counts (where the sparse-data fallback usually triggers anyway).
- No control series: when multiple workspaces/themes provide donor pools, **synthetic difference-in-differences** (Arkhangelsky et al., 2021) is the credible next design, as anticipated in the strategy plan.
- Single-intervention assumption: overlapping actions on the same theme are attributed to the earliest approved execution.

### Suggested references (verify editions/pages)
- Arkhangelsky, D., Athey, S., Hirshberg, D. A., Imbens, G. W., & Wager, S. (2021). Synthetic Difference-in-Differences. *American Economic Review*, 111(12).
- Bernal, J. L., Cummins, S., & Gasparrini, A. (2017). Interrupted time series regression for the evaluation of public health interventions: a tutorial. *International Journal of Epidemiology*, 46(1).
- Halperin, B., Ho, B., List, J. A., & Muir, I. (2022). Toward an Understanding of the Economics of Apologies: Evidence from a Large-Scale Natural Field Experiment. *The Economic Journal*, 132(641). (The "Uber apology" field experiment.)
- Wagner, A. K., Soumerai, S. B., Zhang, F., & Ross-Degnan, D. (2002). Segmented regression analysis of interrupted time series studies in medication use research. *Journal of Clinical Pharmacy and Therapeutics*, 27(4).

### Implementation mapping (for the appendix / reproducibility)
| Design element | Code |
|---|---|
| Segmented-regression fit + CI | `outcome_engine.its_effect` |
| Series construction (UTC days, truncation, exec-day exclusion) | `outcome_engine.its_outcome_for_problem` |
| Contract proposal (trailing baseline, 30d window) | `outcome_engine.propose_outcome_contract` |
| Zero-input application at approval | `routers/problems.py` approval route (`accept_proposed_contract`) |
| Scheduled T+7 / T+30 re-measurement | `measurement_scheduler.py` + `migrations/011` (`clara_run_due_measurements`, pg_cron) |
| Exact-recovery + bias regression tests | `tests/test_outcome_engine.py` |
