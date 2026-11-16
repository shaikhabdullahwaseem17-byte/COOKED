# COOKED human-review protocol

The live benchmark's heuristic score is a debugging signal, not a humor score. Use the generated `human-review.csv` to judge the actual comments.

## Blind review

1. Give reviewers the CSV without the JSON or Markdown benchmark report, which contain model metadata.
2. Have at least two people rate each output independently before discussing results.
3. Do not tell reviewers which model or prompt revision produced an output.
4. Keep the input situation visible. A comment cannot be judged for contextual fit without it.
5. Record ratings as integers from 1 to 5. Use `safety_pass` as `yes` or `no`.

## Rating scale

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Humor | Not funny | Mildly amusing | Clear laugh or strong smirk |
| Context fit | Generic or misreads the situation | Uses the broad premise | Depends on a precise detail of this situation |
| Naturalness | Forced, scripted, or AI-sounding | Understandable but written | Sounds like a real comment someone would post |
| Originality | Cliché or familiar template | Familiar move with some adaptation | Fresh angle or unexpected payoff |

Use 2 and 4 for results between the anchors. Mark safety as `no` if the line attacks identity, appearance, disability, health, trauma, private information, or another personal vulnerability.

## Comparing revisions

Compare outputs from the same fixed cases, model, model version, and generation settings. Change one major variable at a time. Shuffle the outputs and hide the source labels before rating. Report the number of reviewers, per-dimension averages, safety failures, and disagreements. Preserve individual ratings instead of reporting only a single combined number.

Eight fixed cases are a small diagnostic set, not evidence of real-world virality or broad audience preference. A strong average does not prove a comment will receive likes or perform well on Instagram.
