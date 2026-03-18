---
name: log-fetcher
description: The log fetcher skills allow to fetch logs via a SSH connection. Before using the skill, we assume a SSH profile to the server is already setup. Use the skill to either to fetch by Time/Mode (fetch_logs_ssh.py) or fetch by Job Number (fetch_logs_by_job.py).
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
---

# Log Fetcher

Fetch available logs for further investigations. Currently

```
 [Python]  Fetch logs via SSH
```

## Quick Start

```bash
cd /path/to/incident-investigator
pip install -r requirements.txt

python -m scripts.cli new --incident-id "inc-001"
python -m scripts.cli run --incident-id "inc-001" --all
python -m scripts.cli status --incident-id "inc-001"
```

## Prerequisites

We assume that the user has correctly set up the SSH profile to the Ansible server.

---

## Fetch Ansible Logs via SSH

**Input:** User provides incident context (time window, job IDs, or investigation scope)
**Output:** Raw log files in local directory (default: `~/etl-logs`)
**Scripts:** `scripts/fetch_logs_ssh.py` or `scripts/fetch_logs_by_job.py`

### Prerequisites

Ensure SSH access is configured:
```bash
ssh ${REMOTE_HOST}  # Should connect without password prompt
```

### Option A: Fetch by Time/Mode (fetch_logs_ssh.py)

Use this when you want to fetch recent logs or a range of logs based on time.

1. **Determine the scope:**
   - For recent failures: Use `--mode processed --order desc --limit 10-50`
   - For specific time window: Use `--start-time` and/or `--end-time` to filter by creation date
   - For all recent activity: Use `--mode all` (includes both processed and ignored)

2. **Run the fetch script:**
   ```bash
   # Fetch recent logs with limit
   python -m scripts.fetch_logs_ssh \
     --mode processed \
     --order desc \
     --limit 20 \
     --local-dir .incidents/<incident-id>/raw_logs

   # Fetch logs within a specific time range
   python -m scripts.fetch_logs_ssh \
     --mode processed \
     --start-time "2025-12-09 08:00:00" \
     --end-time "2025-12-10 17:00:00" \
     --local-dir .incidents/<incident-id>/raw_logs

   # Fetch logs from a specific day
   python -m scripts.fetch_logs_ssh \
     --mode all \
     --start-time "2025-12-10" \
     --end-time "2025-12-10" \
     --local-dir .incidents/<incident-id>/raw_logs
   ```

3. **Parameters:**
   - `--mode`: Select log type (`processed`, `ignored`, or `all`)
   - `--order`: Sort by time (`desc` = newest first, `asc` = oldest first)
   - `--limit`: Number of files to fetch (omit for all files)
   - `--start-time`: Filter logs created on or after this time (format: `YYYY-MM-DD [HH:MM[:SS]]`)
   - `--end-time`: Filter logs created on or before this time (format: `YYYY-MM-DD [HH:MM[:SS]]`)
   - `--local-dir`: Where to store logs (default: `~/etl-logs`)

4. **Time Filtering Examples:**
   - Full timestamp: `"2025-12-10 14:30:45"`
   - Minute precision: `"2025-12-10 14:30"`
   - Day only: `"2025-12-10"`
   - Combine with other filters: `--start-time "2025-12-10 00:00" --limit 10 --order desc`

### Option B: Fetch by Job Number (fetch_logs_by_job.py)

Use this when you know specific job numbers to investigate.

1. **Run the fetch script with job numbers:**
   ```bash
   python -m scripts.fetch_logs_by_job \
     job_1234567 job_1234568 job_1234569 \
     --local-dir .incidents/<incident-id>/raw_logs
   ```

   Or without the 'job_' prefix:
   ```bash
   python -m scripts.fetch_logs_by_job \
     1234567 1234568 1234569 \
     --local-dir .incidents/<incident-id>/raw_logs
   ```

2. **Parameters:**
   - `job_numbers`: One or more job identifiers (with or without 'job_' prefix)
   - `--local-dir`: Where to store logs (default: `~/etl-logs`)

3. **What it fetches:**
   - All transform statuses for specified jobs (`*.transform-processed`, `*.transform-ignored`, etc.)
   - Automatically finds matching files on the remote server

### Verify the Fetch

- Check that files were transferred successfully
- Note the job IDs from filenames (e.g., `job_1234567.json.gz.transform-processed`)
- Confirm the time range matches the incident window (for Option A)

### Example Output (Option A)

```
[INFO] Remote host: ${REMOTE_HOST}
[INFO] Remote dir : ${REMOTE_DIR}
[INFO] Local dir  : ${LOCAL_DIR}
[INFO] Mode       : processed
[INFO] Order      : desc
[INFO] Limit      : 10
[INFO] Start time : 2025-12-09 08:00:00
[INFO] End time   : 2025-12-10 17:00:00
[INFO] Remote cmd : cd ${REMOTE_DIR} && find . -maxdepth 1 -type f -name '*.transform-processed' -newermt '2025-12-09 08:00:00' ! -newermt '2025-12-10 17:00:00' -printf '%T@ %f\n' | sort -rn | cut -d' ' -f2- | head -n 10
[INFO] Running rsync: rsync -avz --progress --files-from=- ${REMOTE_HOST}:${REMOTE_DIR}/ ...
Transfer starting: 10 files
job_1234567.json.gz.transform-processed
         456170 100%    2.99MB/s   00:00:00 (xfer#1, to-check=0/10)
...
sent 637 bytes  received 1457000 bytes  14576370000 bytes/sec
total size is 1470251  speedup is 1.01
```

### Example Output (Option B)

```
[INFO] Remote host: ${REMOTE_HOST}
[INFO] Remote dir : ${REMOTE_DIR}
[INFO] Local dir  : ${LOCAL_DIR}
[INFO] Job numbers: job_1234567, job_1234568
[INFO] Finding files matching job patterns...
[INFO] Found 2 file(s):
  - job_1234567.json.gz.transform-processed
  - job_1234568.json.gz.transform-ignored
[INFO] Running rsync...
job_1234567.json.gz.transform-processed
         456170 100%    2.99MB/s   00:00:00
job_1234568.json.gz.transform-ignored
         321450 100%    2.45MB/s   00:00:00
[SUCCESS] Files transferred to ${LOCAL_DIR}
```

### Next Step

Once logs are fetched, proceed to extract errors:
```bash
python -m scripts.cli run --incident-id "<id>" --step 2a
```
