# Skill Chaining Experiment Report

There are several approaches to chain skills, including:
1. Using orchestration agent (claude code) to **manually** chaining several skills, through slash commands or English.
2. Using subagent equipped with skills to chain several skills (not possible, see aiops-experiment-logs)
3. Using a single skill to chain several skills (see `incident-investigator/`).
4. Using **subagent** with slash commands to chain several skills (not possible, see aiops-experiment-logs)
5. Using Claude Agent SDK for chaining (see `agent_sdk/`).

Currently, we have tested out approach 1 to 4, with 5 in a separate PR.
* For approach 1, it relies on human in the loop
* For approach 2, it is not viable, see the experiment logs for crash reports.
* For approach 3 and 4, the conclusion is in the following.

To reproduce, put the agents in .claude/agents and register the skills with the claude-plugin. 
Cost Analysis:

| Metric | Approach 3 with Skill within Skill | Approach 4 with SubAgent |
|--------|-----------------------------------|--------------------------|
| Total Cost | $1.18 | $1.96 |
| Total Duration (API) | 2m 59s | 4m 13s |
| Total Duration (Wall) | 5m 41s | 7m 69s |
| Code Changes (Added) | 0 lines | 0 lines |
| Code Changes (Removed) | 0 lines | 0 lines |
| Primary Model Used | claude-opus-4-6 | claude-opus-4-6 |
| Input Tokens (Primary) | 292 | 312 |
| Output Tokens (Primary) | 5.5k | 6.2k |
| Cache Reads (Primary) | 584.5k | 730.3k |
| Cache Writes (Primary) | 65.9k | 64.1k |
