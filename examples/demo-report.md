# ai-attrib report

- repo: `<generated demo repo>`
- revision: `HEAD` @ `synthetic`
- window: 2025-03-03 → 2025-06-25
- commits analysed: **55** (merges excluded)
- declared AI involvement: **33** commits (60.0% of all)

## AI-declared vs human-declared

| metric | AI-declared | Human-declared | all |
|---|---|---|---|
| commits | 33 | 22 | 55 |
| share of all commits | 60.0% | 40.0% | 100.0% |
| authors | 1 | 1 | 2 |
| files / commit (median) | 1 | 1 | 1 |
| files / commit (p90) | 3 | 2 | 3 |
| lines / commit (median) | 10 | 7 | 10 |
| lines / commit (p90) | 47 | 19 | 38 |
| commits touching >10 files | 0.0% | 0.0% | 0.0% |
| modules / commit (median) | 1 | 1 | 1 |
| crosses >3 modules | 3.0% | 0.0% | 1.8% |
| touches tests | 15.2% | 4.5% | 10.9% |
| docs only | 18.2% | 27.3% | 21.8% |
| fix commits | 18.2% | 36.4% | 25.5% |
| rework within 14d | 16.7% | 12.5% | 14.3% |

## Same metric, per commit type

| type | AI n | AI files | AI lines | AI >3 mod | human n | human files | human lines | human >3 mod |
|---|---|---|---|---|---|---|---|---|
| fix | 6 | 1 | 10 | 0.0% | 8 | 1 | 12 | 0.0% |
| docs | 6 | 1 | 1 | 0.0% | 6 | 1 | 1 | 0.0% |
| chore | 8 | 2 | 34 | 0.0% | 3 | 1 | 3 | 0.0% |
| refactor | 6 | 2 | 22 | 16.7% | 2 | 1 | 12 | 0.0% |
| test | 5 | 1 | 5 | 0.0% | 1 | 1 | 3 | 0.0% |
| feat | 2 | 1 | 5 | 0.0% | 2 | 2 | 19 | 0.0% |

## Added-line signals (per 1k commits)

| signal | count | per 1k commits |
|---|---|---|
| console.log | 1 | 18.2 |
| empty-catch | 3 | 54.5 |
| todo-fixme | 2 | 36.4 |

## Baseline window `2025-01-14 → 2025-03-01`

| metric | baseline | current |
|---|---|---|
| commits | 22 | 55 |
| authors | 1 | 2 |
| files / commit (median) | 1 | 1 |
| files / commit (p90) | 2 | 3 |
| lines / commit (median) | 3 | 10 |
| lines / commit (p90) | 18 | 38 |
| commits touching >10 files | 0.0% | 0.0% |
| modules / commit (median) | 1 | 1 |
| crosses >3 modules | 0.0% | 1.8% |
| touches tests | 31.8% | 10.9% |
| docs only | 13.6% | 21.8% |
| fix commits | 40.9% | 25.5% |
| rework within 14d | 22.2% | 14.3% |

## How to read this

- **Declared, not detected.** A commit only counts as AI-declared when its message carries a trailer such as `Co-authored-by: Claude`. Silent AI use is invisible, so the AI share is a floor, not an estimate.
- **Rework is a proxy.** It counts `fix` commits that are followed by another `fix` on the same file within 14 days. It cannot tell a regression from an iterative refinement.
- **Small groups are noise.** With fewer than ~20 commits per group, treat differences as directional only.
