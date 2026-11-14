# CodeQL (guidance)

CodeQL is free on public repositories. Use **default setup**, not a workflow file, so there is no
workflow to pin or maintain (ecosystem 7).

1. Enable it per public repository, including the `actions` language:

   ```bash
   gh api -X PATCH repos/gonzalomartinperez/REPO/code-scanning/default-setup \
     -f state=configured -f query_suite=default
   gh api repos/gonzalomartinperez/REPO/code-scanning/default-setup   # verify languages and state
   ```

2. Keep the default query suite; raise it to `extended` only with a measured false-positive rate.
3. Alerts are triaged weekly together with the vulnerability tracker; dismissals carry a reason.
4. Private repositories (`vps-ops`, `pequeverso-marketing`, `dropshipping-ops`): CodeQL needs GitHub
   Advanced Security there (unverified price and availability). Rely on zizmor, osv-scanner and the
   repository linters instead; revisit if the plan changes.

Scorecard's `SAST` check reads the default setup, so no extra workflow is needed for the score.
