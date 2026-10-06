# Airbnb Data Pipeline

A **serverless, scheduled web-scraping pipeline** built end to end on AWS. A Python +
Playwright scraper collects Airbnb listing data and stores it in a cloud database —
containerized, continuously deployed, and run automatically on a daily schedule with
**no servers to manage and no human in the loop**.

> The focus of this repository is the **DevOps engineering** around the scraper: how it's
> built, shipped, run, scheduled, and observed.

---

## Architecture

![Architecture](architecture.png)

Every push to `main` builds the image and publishes it to Amazon ECR. EventBridge triggers
the task on a daily cron; ECS Fargate pulls the image, fetches the database credential from
Secrets Manager, scrapes headlessly, writes results to MongoDB Atlas, and streams logs to
CloudWatch — then shuts down.

---

## Tech Stack

| Area | Technology |
|------|------------|
| Scraper | Python, Playwright, pandas |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Image registry | Amazon ECR (private) |
| Compute | AWS ECS Fargate (serverless) |
| Secrets | AWS Secrets Manager |
| Scheduling | Amazon EventBridge Scheduler |
| Database | MongoDB Atlas |
| Logging | Amazon CloudWatch Logs |

---

## What This Project Demonstrates

- **Full DevOps lifecycle for a batch workload** — build → containerize → CI/CD → registry
  → serverless run → secrets → persistence → scheduling.
- **Serverless, cloud-native design** — no servers to provision, patch, or keep running;
  pay only for the minutes the job runs.
- **Secrets & configuration management** — credentials injected at runtime from Secrets
  Manager (never in the code); behavior driven by environment variables.
- **IAM** — users, roles, task execution role, trust policies, least-privilege awareness.
- **Workload-appropriate architecture** — a scheduled batch job (this) is deployed very
  differently from an always-on web service.

---

## How It Works

### CI/CD (`.github/workflows/ci-cd.yml`)
On every push to `main`, GitHub Actions checks out the code, authenticates to AWS, logs in
to ECR, builds the Docker image, and pushes it — tagged for the registry.

### Scheduled run (AWS)
Amazon EventBridge Scheduler fires on a cron schedule and launches the task on ECS Fargate.
The task's execution role lets it pull the image from ECR, read the `MONGODB_URI` secret
from Secrets Manager, and write logs to CloudWatch. The scraper runs headless, saves each
listing to MongoDB Atlas, and the container exits.

---

## Running It

**Automated:** runs itself daily via EventBridge — nothing to do.

**Interactive (local, for ad-hoc searches):**
```bash
# Linux/macOS
export HEADLESS=false
export MONGODB_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Airbnb"
python main.py
```
```powershell
# Windows PowerShell
$env:HEADLESS = "false"
$env:MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Airbnb"
python main.py
```

Configuration is read from environment variables (`DESTINATION`, `CHECKIN`, `CHECKOUT`,
`ADULTS`, …), with sensible defaults — so the same image runs both interactively and on
the cloud schedule.

---

## Project Structure

```
.
├── .github/workflows/ci-cd.yml   # CI/CD: build + push to Amazon ECR
├── Dockerfile                    # Playwright base image, headless-ready
├── requirements.txt              # Direct dependencies only
├── main.py                       # Scraper + MongoDB persistence
└── architecture.png              # Architecture diagram
```

---

## Known Limitations

- **Anti-bot blocking:** Airbnb intermittently blocks data-center (cloud) IPs, so some
  runs return no listings. The pipeline is unaffected — the target site blocks the request.
  Hardening would add retries, proxies, or stealth techniques.
- **Hotel descriptions:** the description parser targets apartment-style pages; hotel pages
  use a different layout, so that single field is sometimes empty (all other fields are
  captured). Fix = a hotel-specific parser.
- **Demo-level security:** open network access and broad IAM policies were used for speed;
  production would scope network access to specific IPs, use least-privilege custom
  policies, and use OIDC instead of long-lived keys in CI.

---

## Author

**Zeeshan Ali Qureshi** — DevOps / Cloud Engineer
[GitHub](https://github.com/Zeeshan0335)
