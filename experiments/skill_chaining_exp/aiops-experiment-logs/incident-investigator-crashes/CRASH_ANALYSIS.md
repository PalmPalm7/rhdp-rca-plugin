# Incident Investigator Simple Agent Crash Analysis

**Analysis Date:** 2026-01-30
**Analyzed Sessions:** 4 sessions from 2026-01-29

## Summary

The `incident-investigator-simple` agent consistently fails/crashes when invoked. All 4 analyzed sessions show the same failure pattern.

## Session Details

| Session ID | Start Time | Issue |
|-----------|------------|-------|
| `aaaaaaaa-1111-4000-a000-aaaaaaaaa001` | 19:30:02 | Agent hangs after Skill invocation |
| `aaaaaaaa-1111-4000-a000-aaaaaaaaa002` | 19:34:06 | Agent hangs after Skill invocation |
| `aaaaaaaa-1111-4000-a000-aaaaaaaaa003` | 19:36:44 | Agent hangs after Skill invocation |
| `aaaaaaaa-1111-4000-a000-aaaaaaaaa004` | 19:41:24 | Agent hangs after Skill invocation |

## Root Cause Analysis

### Primary Issue: Skill Tool Invocation Failure

The agent definition in `incident-investigator-simple.md` instructs the agent to:
1. Use `/log-fetcher` skill
2. Use `/root-cause-analysis` skill
3. Use `/context-fetcher` skill

**The Problem:** When the incident-investigator-simple agent attempts to invoke these skills via the `Skill` tool, the session appears to hang indefinitely and eventually times out or is terminated.

### Evidence from Logs

From the conversation jsonl (session `aaaaaaaa-1111-4000-a000-aaaaaaaaa004`):
```json
{
  "type": "tool_use",
  "id": "toolu_placeholder_example_id",
  "name": "Skill",
  "input": {
    "skill": "log-fetcher",
    "args": "--limit 20 --sort desc --mode all"
  }
}
```

After this Skill invocation, there is a ~90 second gap with no activity in the debug logs before the session ends with `[REPL:unmount]`.

### Debug Log Timeline (Session b407a9d4)

```
19:41:43.340Z - SubagentStart query: incident-investigator-simple
19:41:47.180Z - API request for agent (last successful API call)
19:43:12.483Z - [REPL:unmount] REPL unmounting (session termination)
```

This ~85 second gap with no API activity suggests the Skill invocation is blocking or causing a hang.

## Potential Root Causes

### 1. Missing Skill Definitions
The skills referenced in the agent (`log-fetcher`, `root-cause-analysis`, `context-fetcher`) may not be properly registered or available.

From the debug logs:
```
Loaded 0 unique skills (managed: 0, user: 0, project: 0, legacy commands: 0)
```

This indicates no custom skills were loaded from the project directory.

### 2. Nested Agent/Skill Invocation Issue
When a subagent (launched via Task tool) attempts to invoke a Skill, there may be an architectural limitation or bug preventing nested tool invocations.

### 3. Skill Registration Path
The skills are likely located in the project but not in the expected path. The logs show:
```
Loading skills from: managed=/Library/Application Support/ClaudeCode/.claude/skills,
                     user=/Users/<user>/.claude/skills,
                     project=[]
```
Note that `project=[]` is empty - skills in `.claude/skills/` within the project directory may not be getting loaded.

## Secondary Issues Observed

### API Beta Header Error
```
API error (attempt 1/11): 400 400 {"type":"error","error":{"type":"invalid_request_error",
"message":"Unexpected value(s) `structured-outputs-2025-12-15` for the `anthropic-beta` header..."}}
```
This error occurs but is handled with a fallback, so it's not the primary cause of crashes.

### GitHub MCP Plugin Connection Failure
```
MCP server "plugin:github:github": Connection failed after 797ms:
Streamable HTTP error: Error POSTing to endpoint: bad request: Authorization header is badly formatted
```
This is a separate issue (missing/misconfigured GITHUB_PERSONAL_ACCESS_TOKEN).

## Recommendations

1. **Verify Skill Registration**: Ensure the skills (`log-fetcher`, `root-cause-analysis`, `context-fetcher`) are properly defined and located in a path that Claude Code scans.

2. **Check Skills Directory Structure**: Skills should be in:
   - `/Users/<user>/.claude/skills/` (user-level)
   - Or properly configured in the project's `.claude/` directory

3. **Test Skills Independently**: Before using the incident-investigator-simple agent, test each skill directly:
   ```
   /log-fetcher --limit 5
   /root-cause-analysis
   /context-fetcher
   ```

4. **Consider Tool Access**: The agent definition has `allowed-tools` commented out. Consider uncommenting and specifying the Skill tool explicitly.

5. **Alternative Approach**: Instead of using nested skills, have the agent directly use Bash/Read/Grep tools to perform log fetching and analysis.

## Files Included in This Report

- `aaaaaaaa-1111-4000-a000-aaaaaaaaa001.txt` - Debug log session 1
- `aaaaaaaa-1111-4000-a000-aaaaaaaaa002.txt` - Debug log session 2
- `aaaaaaaa-1111-4000-a000-aaaaaaaaa003.txt` - Debug log session 3
- `aaaaaaaa-1111-4000-a000-aaaaaaaaa004.txt` - Debug log session 4

## Agent Definition Reference

```markdown
---
name: incident-investigator-simple
description: Use this agent when the user wants to perform an end-to-end incident
investigation workflow that fetches logs and performs root cause analysis.
model: inherit
---

## Phase 1: Fetch Logs - Use log-fetcher skill /log-fetcher
## Phase 2: Perform Root Cause Analysis - Use root-cause-analysis skill /root-cause-analysis
## Phase 3: Fetch contexts - Use context-fetcher skill /context-fetcher
```
