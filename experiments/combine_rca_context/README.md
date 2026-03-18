# Combine RCA Context Experiments

Experimental work comparing three approaches (v1, v2, v3) for integrating AgnosticD/AgnosticV configuration analysis into root-cause-analysis.

## Background

The **original root-cause-analysis** only correlates AAP logs with Splunk pod logs. These experiments add GitHub-based configuration analysis to provide deeper root cause insights.

## Key Differences

| Version | GitHub Fetching | Workflow | Key Feature |
|---------|----------------|----------|-------------|
| **Original** | None | Log correlation only | Baseline - no config analysis |
| **v1** | Manual (Claude uses MCP) | Steps 1-3 automated, Step 4 manual | Adds config analysis capability |
| **v2** | Semi-automated (Python parses, Claude fetches) | Steps 1-4a automated, Steps 4b-4e manual | Structured path parsing |
| **v3** | **Fully automated (Python GitHub API)** | **Steps 1-4 automated, Step 5 manual** | **Automated fetching + verification** |

## Results
compared across three production jobs (job IDs anonymized for privacy).
| Version | Accuracy | Avg Cost | Status |
|---------|----------|----------|--------|
| Original | ~6.0/10 | ~$0.30 | Baseline |
| v1 | 7.0/10 | $0.50 | Manual fetching |
| v2 | 8.0/10 | $0.55 | Semi-automated |
| **v3** | **9.5/10** | **$0.37** | **Fully automated** |

## Conclusion

**v3 wins** - Best accuracy (9.5/10), lowest cost ($0.37), fastest execution. Fully automated GitHub fetching reduces Claude token usage by 32-49% while providing better accuracy through actual file verification

Note:

I've done repeat comparisons on these 3 versions, due to the uncertainty of llm, each time the cost is a bit different and also the accuracy, but generally v3 is cheaper than the other 2 version. and accuracy is on par.

## For More Details


- **Implementations**: `v1/`, `v2/`, `v3/` - Experimental code
- **Output logs, cost metrics, claude accuracy eval**  [link (red hat only)](https://drive.google.com/drive/folders/1YxiGXgVl0XKIqkpl9bWgctQz8RXUkIkx?usp=sharing) including:
    * `rca_comparison_analysis.md` - Complete comparison, cost breakdowns, job-by-job analysis
    * cost metrics: token usage, money, time, cache, read, write, token by model.
    * output logs per job.
