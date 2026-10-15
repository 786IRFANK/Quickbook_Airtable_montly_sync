# QuickBooks → Airtable Monthly Sync

Retrieves monthly payment transaction statements from QuickBooks and stores them in Airtable. The workflow is scheduled to run automatically once per month and is hosted on an AWS EC2 instance.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Installation](#installation)
- [Running the Sync](#running-the-sync)
- [Scheduling on EC2](#scheduling-on-ec2)
- [Airtable Schema](#airtable-schema)
- [Logging and Monitoring](#logging-and-monitoring)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Maintenance](#maintenance)

---

## Overview

| Item | Detail |
|------|--------|
| **Source** | QuickBooks Online (Payments / transaction reports) |
| **Destination** | Airtable base |
| **Frequency** | Once per month (automated) |
| **Hosting** | AWS EC2 instance |
| **Scheduler** | cron (or systemd timer) on the EC2 host |

The sync pulls the previous month's payment transactions from QuickBooks and upserts them into Airtable so the data can be used for reporting, reconciliation and client statements.

## How It Works

1. The scheduler triggers the sync on the 1st of each month.
2. The script refreshes the QuickBooks OAuth2 access token using the stored refresh token.
3. It determines the date range for the previous calendar month.
4. It fetches payment transactions for that range from the QuickBooks API (with pagination).
5. Each transaction is mapped to the Airtable field schema.
6. Records are upserted into Airtable in batches of 10 (Airtable API limit), keyed on the QuickBooks transaction ID so reruns do not create duplicates.
7. A summary (records fetched / created / updated / failed) is written to the log.

## Architecture

```
┌──────────────┐   cron    ┌────────────────────────┐
│  AWS EC2     │ ────────► │  sync script           │
│  (Linux)     │           │  (monthly run)         │
└──────────────┘           └───────┬────────┬───────┘
                                   │        │
                      OAuth2 / REST│        │REST (batch upsert)
                                   ▼        ▼
                          ┌─────────────┐ ┌─────────────┐
                          │ QuickBooks  │ │  Airtable   │
                          │ Online API  │ │  Base/Table │
                          └─────────────┘ └─────────────┘
```

## Prerequisites

- AWS EC2 instance (Linux, e.g. Ubuntu 22.04) with outbound HTTPS access
- Python 3.10+ (or the runtime your implementation uses)
- QuickBooks Online developer app (Client ID, Client Secret, Realm/Company ID)
- Airtable personal access token with `data.records:read` and `data.records:write` scopes on the target base
- Git, pip, and a virtual environment tool

## Configuration

All secrets and settings are supplied through environment variables (never commit them).

Create a `.env` file in the project root:

```env
# QuickBooks
QB_CLIENT_ID=your_client_id
QB_CLIENT_SECRET=your_client_secret
QB_REALM_ID=your_company_id
QB_REFRESH_TOKEN=your_refresh_token
QB_ENVIRONMENT=production        # or sandbox

# Airtable
AIRTABLE_TOKEN=your_personal_access_token
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Payments

# Sync behavior
SYNC_MONTH=                      # optional override, format YYYY-MM (defaults to previous month)
LOG_LEVEL=INFO
```

> **Note:** QuickBooks rotates refresh tokens. The script must persist the latest refresh token after each run (e.g. in a local file or AWS SSM Parameter Store) or the next run will fail authentication.

## Installation

```bash
# 1. Connect to the EC2 instance
ssh -i your-key.pem ubuntu@<ec2-public-ip>

# 2. Clone the repository
git clone <repository-url> quickbooks-airtable-sync
cd quickbooks-airtable-sync

# 3. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
cp .env.example .env
nano .env
```

## Running the Sync

Run manually for the previous month:

```bash
source venv/bin/activate
python sync.py
```

Run for a specific month (backfill):

```bash
SYNC_MONTH=2026-08 python sync.py
```

Because records are upserted on the QuickBooks transaction ID, it is safe to re-run a month.

## Scheduling on EC2

Add a cron entry to run at 02:00 UTC on the 1st of every month:

```bash
crontab -e
```

```cron
0 2 1 * * cd /home/ubuntu/quickbooks-airtable-sync && /home/ubuntu/quickbooks-airtable-sync/venv/bin/python sync.py >> /var/log/qb_airtable_sync.log 2>&1
```

Verify:

```bash
crontab -l
```

Make sure the EC2 instance is running at the scheduled time. If the instance is stopped on a schedule to save cost, use an EventBridge rule to start it before the job, or move the job to a systemd timer with `Persistent=true` so missed runs execute on boot.

## Airtable Schema

Expected fields in the target table (adjust to match your base):

| Field | Type | Source |
|-------|------|--------|
| Transaction ID | Single line text (unique key) | QuickBooks `Id` |
| Date | Date | `TxnDate` |
| Customer | Single line text | `CustomerRef.name` |
| Amount | Currency | `TotalAmt` |
| Payment Method | Single line text | `PaymentMethodRef.name` |
| Reference No. | Single line text | `PaymentRefNum` |
| Deposit Account | Single line text | `DepositToAccountRef.name` |
| Statement Month | Single line text (`YYYY-MM`) | Derived |
| Synced At | Date/time | Run timestamp |

## Logging and Monitoring

- Logs are written to `/var/log/qb_airtable_sync.log` (or the path set in your cron entry).
- Each run logs: date range, records fetched, created, updated, failed, and total runtime.
- Recommended: configure a CloudWatch alarm or email/Slack alert on a non-zero exit code or missing run.

Check the latest run:

```bash
tail -n 100 /var/log/qb_airtable_sync.log
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `401 Unauthorized` from QuickBooks | Expired or rotated refresh token | Re-authorize via the QuickBooks OAuth playground and update the stored refresh token |
| `invalid_grant` on token refresh | Refresh token expired (not used for 100+ days) | Re-authorize the app |
| `422` from Airtable | Field name/type mismatch | Confirm table fields match the schema above |
| `429` from Airtable | Rate limit (5 req/sec per base) | Script should back off and retry; reduce batch frequency |
| No records synced | Wrong month or no payments | Check `SYNC_MONTH` and the QuickBooks date range |
| Job did not run | EC2 stopped or cron misconfigured | Check `crontab -l`, instance uptime, and `/var/log/syslog` |

## Security Notes

- Keep `.env` out of version control (`.gitignore`) and restrict permissions: `chmod 600 .env`.
- Prefer AWS SSM Parameter Store or Secrets Manager for credentials in production.
- Restrict the EC2 security group to SSH from trusted IPs only.
- Use an Airtable token scoped to only the required base.

## Maintenance

- Review QuickBooks app credentials and token validity periodically.
- Keep dependencies updated: `pip list --outdated`.
- Spot-check the Airtable totals against the QuickBooks monthly report after each run.
- Back up the Airtable base according to your data retention policy.
