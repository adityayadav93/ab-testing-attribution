# Experiment Design: One-Page Checkout Redesign

*Written before analysing outcomes. Metric definitions, error rates and segments below are what the analysis notebook implements.*

## 1. Hypothesis and decision

**Hypothesis.** Replacing the three-step checkout with a one-page checkout increases the share of visitors who complete a purchase.

**Decision rule.** Ship if (a) conversion lift is statistically significant at alpha = 0.05, (b) revenue per visitor is not lower, and (c) the refund guardrail is non-inferior. Otherwise keep the current checkout.

## 2. Design

| Item | Choice |
|---|---|
| Unit of randomisation | User (cookie-based), 50/50 split |
| Duration | 14 days (2 to 15 Mar 2026), covering two full weekly cycles |
| Population | All site visitors who reach the cart |
| Exposure | Assigned at first cart view; one assignment per user |

## 3. Metrics

| Role | Metric | Definition |
|---|---|---|
| **Primary** | Conversion rate | Users with a purchase / users assigned |
| Secondary | Revenue per visitor (RPV) | Order revenue / users assigned (zero for non-buyers) |
| Secondary | Average order value (AOV) | Revenue / orders |
| **Guardrail** | Refund rate | Refunded orders / orders; non-inferiority margin +1.5 pts |
| Covariate | Pre-period spend | User's spend in the 30 days before assignment (CUPED) |

## 4. Statistical plan

| Item | Choice |
|---|---|
| Significance | alpha = 0.05, two-sided |
| Power | 80% for the primary metric |
| Minimum detectable effect | +8% relative on a 5.0% baseline (0.4 pts absolute) |
| Required sample | about 48,300 users per arm (Cohen's h, normal approximation) |
| Primary test | Two-proportion z-test; Newcombe CI for the difference; log relative-risk CI |
| Revenue metrics | Welch t-test, nonparametric bootstrap (2,000 resamples), CUPED-adjusted estimate |
| Guardrail | Upper bound of the 95% CI for the refund-rate difference must be below the margin |
| Segments (pre-specified) | Device (mobile, desktop, tablet) and customer type (new, returning); Holm correction across the five tests; likelihood-ratio interaction test for device |
| No peeking | Analysed once, at the planned end date |

## 5. Validity checks (run before interpreting results)

1. **Sample ratio mismatch:** chi-square test on arm sizes; investigate if p < 0.001.
2. **Covariate balance:** device mix, customer type and pre-period spend compared across arms.
3. **Stability:** daily and cumulative lift; week 1 versus week 2 compared with an interaction test (novelty check).

## 6. Guardrail power note

Only about 3,100 orders per arm are expected, so the refund-rate difference has a standard error of about 0.6 pts. At that precision the test has roughly 26% power to demonstrate non-inferiority at a 1.0 pt margin, 58% at 1.5 pts, and 85% at 2.0 pts (assuming a true +0.2 pt difference). A 1.5 pt margin was used as a compromise between a tight margin and a feasible test; it can rule out large refund increases but not small ones, so post-launch monitoring is part of the plan.

## 7. Business impact model

Annualised incremental revenue = RPV difference x annual visitors. Annual traffic of 3.0M unique visitors is an assumption to replace with the actual figure.

## 8. Known limitations

- Two weeks may miss monthly purchase cycles and promotions.
- Results describe visitors who reach the cart, not all site traffic.
- Segment results beyond the pre-specified five are exploratory.
