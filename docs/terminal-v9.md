# Institutional GPU pricing dashboard

This release changes presentation and inspection controls. All official forecasts, histories, research results, registered protocols and training gates remain unchanged.

The dashboard uses a navy navigation shell, cool neutral surfaces, tabular figures, compact quote statistics and a dominant source-matched timeline. The observed record, archived forecast and scenario calculations stay separate. Historical gaps remain gaps. The quote strip uses the last publishable matching observation and the actual endpoint quantiles; its percentage is the forecast median divided by the last observation minus one, not a realized return.

Fit range uses a linear price axis over the visible observed and forecast values, with 16% padding around the visible span (minimum span 5% of maximum price). The lower bound is floored at zero. A visible axis label identifies the fitted range. Zero base restores the original zero-based price scale. Switching the axis changes geometry only; source values, calendar spacing, quantiles and immutable pins stay unchanged.

Scenarios retain the published annual assumptions and monthly compounding. Research retains the negative primary v8 finding and all denominator/fallback disclosures. No live-data badge, simulated activity, invented historical prices or new forecasting result is introduced.

Remote PNG-only checks cover desktop and mobile views, first-screen chart visibility, source-bound statistics, fit/zero geometry, unchanged source values, scenario arithmetic, navigation, keyboard and pin preservation. Existing required validation suites remain strict.

Refreshes publish the two research responses into the view together. Keyboard focus returns to Refresh when it initiated the operation and the user has not moved elsewhere. Date-axis labels suppress an intermediate tick when it would collide with the end date; dates and cutoff markers remain unchanged.
