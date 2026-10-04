# FraudShield AI

**Real-time fraud operations platform for banks.** FraudShield AI screens digital payments (UPI, QR, card), scores each one with a rule engine and a machine-learning model, explains why a payment was flagged, and gives fraud analysts a case queue to review and decide on it, with supervisor approval for high-value actions.

> **Project status: working prototype.**
> The dashboard UI, rule definitions and risk-tier logic are built. The live alert feed, model scores, SHAP explanations, scam checker and model metrics currently use **simulated sample data**. Items marked 🚧 below are being wired to the real backend. Do not treat any figure shown in the demo as a real result.

---

## Screenshots

Add screenshots to `docs/screenshots/` and link them here:

| Screen | File |
|---|---|
| Overview | `docs/screenshots/overview.png` |
| Case queue | `docs/screenshots/case-queue.png` |
| Case detail (SHAP + audit log) | `docs/screenshots/case-detail.png` |
| Rules & Models | `docs/screenshots/rules-models.png` |
| Scam Intelligence | `docs/screenshots/scam.png` |

---

## Features

### 1. Overview
A live risk pulse and KPI cards for the last 24 hours:
- Payments screened
- Open cases (split by high / medium risk)
- Cases past SLA
- Value awaiting decision (₹)
- Fraud prevented (₹ in confirmed blocked transfers)

Also shows a 12-hour bar chart of screened vs. flagged volume, and the alert distribution by rule.

### 2. Case Queue
A work queue of flagged payments with:
- SLA countdown per case ("9m left")
- Customer name and segment (Salaried, Business, Student, Senior citizen)
- Amount, channel (UPI / QR / CARD), payee handle
- Risk tier (HIGH / MEDIUM) and the rules that triggered
- Search, plus filters for status, risk tier and channel
- Live toast notification when a new case is flagged

### 3. Case Detail (Investigation Console)
Opens a case with:
- **Risk score** (0–100) and the **SHAP feature-importance** panel showing which signals pushed the score up or down 🚧 (real SHAP planned)
- Transaction overview: customer, account, branch, average monthly spend, amount, channel, payee
- Triggered detection rules with a plain-language explanation
- **Audit history and action log**
- A **required decision note** and four actions:
  - **Approve / Release**
  - **Hold for Customer Call**
  - **Block Payment**
  - **Confirm Fraud**

### 4. Payments
List of all screened payments. Low-risk payments are auto-cleared. 🚧 Planned: a "Test a payment" form that runs a payment through the full pipeline (features → model → rules → risk tier → SHAP).

### 5. Rules & Models
- **Deterministic rule management**: each rule shows its specification, trigger hits, precision and an on/off toggle.
- **ML classifier metrics**: precision, recall, F1 and ROC-AUC per model. 🚧 Currently placeholder numbers; they will be replaced by results from `ml/train.py`.

### 6. Scam Intelligence
Paste a suspicious SMS, WhatsApp message or call transcript (e.g. digital-arrest or KYC scams) and get an analysis. 🚧 Currently keyword matching; LLM-based analysis is planned.

### 7. Maker-checker control
An analyst who tries to **block a payment or confirm fraud above ₹50,000** sends the case to a supervisor for approval instead of finalising it. 🚧 Enforced in the backend once the decision endpoint is live.

---

## Detection rules

| # | Rule | Condition |
|---|---|---|
| 1 | Large payment to new payee | Over ₹50,000 to a payee the customer has never paid before |
| 2 | Rapid small payments | 3 or more payments of ₹100 or less to one payee within 5 minutes (UPI testing pattern) |
| 3 | Unusual hour transaction | Over ₹10,000 transferred between midnight and 5 AM |
| 4 | High-value QR, new merchant | Over ₹20,000 via QR code to a newly scanned merchant |
| 5 | Large payment after 30+ quiet days | Sudden high-value transfer (over ₹50,000) after prolonged account dormancy (digital-arrest scam pattern) |

### Risk tiers

Each payment gets a score from the ML model and a list of matched rules, combined into a tier:

| Tier | Rule |
|---|---|
| **High** | ML probability ≥ 0.8, or 2+ rules matched |
| **Medium** | ML probability ≥ 0.4, or 1 rule matched |
| **Low** | Everything else, auto-cleared |

High and Medium cases go to the Case Queue with an SLA timer.

---

## Architecture

```
   Payment (UPI / QR / CARD)
              │
              ▼
   ┌────────────────────┐
   │  FastAPI backend   │
   │  build_features()  │  ← same function used in training and serving
   └─────────┬──────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
 Rule engine     ML model (XGBoost; BiLSTM-CNN optional)
 (5 UPI rules)   → fraud probability
     └───────┬────────┘
             ▼
     compute_risk_score()  → Low / Medium / High
             │
     ┌───────┼──────────────┐
     ▼       ▼              ▼
 PostgreSQL  Redis pub/sub  SHAP explanation
 (cases,     (High-risk     (TreeExplainer)
 audit log)  alerts)
             │
             ▼  WebSocket /ws/alerts
   ┌────────────────────┐
   │  Dashboard (HTML)  │  Overview · Case Queue · Case Detail ·
   │  served by FastAPI │  Payments · Rules & Models · Scam Intelligence
   └────────────────────┘
```

**Tech stack:** Python, FastAPI, SQLAlchemy / Alembic, PostgreSQL, Redis, XGBoost, TensorFlow/Keras (BiLSTM-CNN), scikit-learn, imbalanced-learn (SMOTE), SHAP, vanilla HTML/CSS/JS dashboard.

---

## Machine learning

| Item | Detail |
|---|---|
| Live model data | [PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) (synthetic mobile money) |
| Comparison data | [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection) (report only; different columns, trained separately) |
| Scam checker testing | [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms-spam-collection) (optional) |
| Models | XGBoost baseline (serving model) and BiLSTM-CNN, selectable by config flag |
| Imbalance handling | Stratified split, SMOTE on the training set only |
| Explainability | SHAP `TreeExplainer` on the XGBoost model |

**Features** are limited to what a bank knows at payment time: amount, hour, sender balance before the payment, and payment type. PaySim's `newbalanceOrig` / `newbalanceDest` leak the answer and are deliberately excluded.

### Known limitations
- **Synthetic data.** PaySim is synthetic and no public dataset covers UPI. This is why the five UPI rules and the transaction simulator matter.
- **Undersampled training set.** The training script keeps all 8,213 fraud rows but only 400,000 legitimate rows so SMOTE and the LSTM train in reasonable time. **Reported scores are more optimistic than real-world performance.**
- **Placeholder metrics.** Until `ml/train.py` is run on the real data, the metrics shown in the dashboard are not real results.
- Rule "precision" values shown in the demo are sample figures.

---

## Getting started

> Commands below are the intended setup. Adjust paths to your repository layout.

### Prerequisites
Python 3.10+, Docker, and a Kaggle account with API token (`~/.kaggle/kaggle.json`).

### 1. Install
```bash
python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary redis \
            pandas numpy scikit-learn imbalanced-learn xgboost tensorflow shap joblib \
            python-jose passlib bcrypt python-multipart websockets pytest kaggle
```

### 2. Start Postgres and Redis
```bash
docker run -d --name fs-postgres -e POSTGRES_PASSWORD=devpass -p 5432:5432 postgres:16
docker run -d --name fs-redis -p 6379:6379 redis:7
```

### 3. Configure
Create a `.env` file (never commit it):
```
DATABASE_URL=postgresql://postgres:devpass@localhost:5432/postgres
REDIS_URL=redis://localhost:6379
JWT_SECRET=change-me
LLM_API_KEY=            # optional, for the scam checker
```

### 4. Get the data and train
```bash
kaggle datasets download -d ealaxi/paysim1 -p data/raw/paysim --unzip
cd ml
python train.py --csv ../data/raw/paysim/PS_20174392719_1491204439457_log.csv
```
Metrics are written to `ml/reports/baseline_metrics.json` and `ml/reports/bilstm_metrics.json`.

### 5. Run the app
```bash
uvicorn app.main:app --reload --port 8000
```
Open **http://127.0.0.1:8000**.

### 6. Simulate live traffic
```bash
python ml/scripts/simulate_transactions.py
```

---

## API (planned)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/login` | Log in, receive JWT (roles: analyst, supervisor) |
| GET | `/alerts` | List flagged cases |
| GET | `/customers` | List customers |
| POST | `/alerts/{id}/decision` | Body `{action, note}`; actions: `released`, `held`, `blocked`, `fraud`, `escalated`. Writes an audit-log row and enforces the ₹50,000 supervisor rule |
| GET | `/transactions/{id}/explanation` | SHAP top features for a transaction |
| GET | `/models/metrics` | Real model metrics |
| WS | `/ws/alerts` | Live push of new High-risk cases |

---

## Roadmap

- [ ] Run `train.py` on PaySim and replace placeholder metrics
- [ ] Real SHAP explanations on the real features
- [ ] Backend pipeline, database, decision endpoint, audit log
- [ ] Login and roles (analyst / supervisor)
- [ ] Replace the demo timer with the `/ws/alerts` WebSocket
- [ ] "Test a payment" form
- [ ] Realistic transaction simulator (all five rules fire, varied payees)
- [ ] LLM-based scam checker
- [ ] pytest suite, Docker Compose, GitHub Actions CI
- [ ] Locust load test and demo video

---

## Testing
```bash
pytest
```
Covers the rule engine, risk scoring, auth, the maker-checker rule and the decision endpoint (in progress).

---

## Team
Ganesha CP Tech, Software Department, Mumbai
- Vaibhav Mane: Data Lead
- Ayurshi Adesh Kadam
- Saim Shahabuddin Fakih

*Confidential internal project. Do not commit raw datasets (Kaggle terms restrict redistribution).*
