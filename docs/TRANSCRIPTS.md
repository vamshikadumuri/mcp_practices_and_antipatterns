# Benchmark report — `test_run`

| Scenario | Server | Turns | Input tok | Output tok | Cache read | Wall s |
|---|---|---:|---:|---:|---:|---:|
| failed_jobs_triage | classic | 3 | 1000 | 200 | 0 | 5.2 |
| failed_jobs_triage | codemode | 3 | 1000 | 200 | 0 | 5.2 |

## Totals
| Server | Total turns | Total input | Total output |
|---|---:|---:|---:|
| classic | 3 | 1000 | 200 |
| codemode | 3 | 1000 | 200 |

**Code Mode saved 0.0% of total tokens vs. classic.**

## Transcripts

### failed_jobs_triage

> Test prompt

#### classic

**Tool calls:**

- `list_batch_jobs({"status": "FAILED"})`

**Final answer:**

Test answer

#### codemode

**Tool calls:**

- `list_batch_jobs({"status": "FAILED"})`

**Final answer:**

Test answer
