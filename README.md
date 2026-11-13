# Complex Code Testing Dashboard

A professional, fully automated Python code quality analysis dashboard for a 7th-semester Software Testing academic project.

## Features

| Module | Tool | Description |
|--------|------|-------------|
| Dynamic Testing | PyTest | Automated test generation and execution |
| Coverage Analysis | Coverage.py | Statement and branch coverage measurement |
| Static Analysis | Flake8 + Pylint | Code smells, unused vars, naming issues |
| Security Analysis | Bandit | eval/exec, hardcoded credentials, shell injection |
| Coding Standards | Pycodestyle | PEP 8 compliance checking |
| Complexity | Radon | McCabe Cyclomatic Complexity analysis |
| Defect Prediction | Heuristic Engine | Rule-based defect risk scoring |

**25 test criteria** across 5 tools, plus cyclomatic complexity analysis and defect prediction.

## Local Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd complex-code-test-dashboard

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

Open http://localhost:5000 in your browser.

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard UI |
| GET | `/api/health` | Health check |
| POST | `/api/analyze` | Submit code for analysis (JSON body) |
| POST | `/api/analyze/upload` | Upload a `.py` file |
| GET | `/api/results/<id>` | Retrieve analysis results |
| GET | `/api/report/<id>?format=json` | Download JSON report |
| GET | `/api/report/<id>?format=html` | Download HTML report |
| GET | `/api/samples` | List sample programs |

### POST /api/analyze

```json
{
  "code": "def add(a, b):\n    return a + b",
  "filename": "my_code.py"
}
```

## Deployment (Render)

1. Push to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
5. Add environment variable `SECRET_KEY` with a secure random value

### ⚠️ Security Limitation

Submitted code is executed in an isolated subprocess with timeout restrictions. Full OS-level sandboxing (seccomp, containers) is **not** available on standard Render free-tier deployments. Do **not** expose this service publicly without additional security measures. For production use, consider:

- Running the application inside a Docker container with restricted capabilities
- Using a dedicated sandboxed execution environment (e.g., AWS Lambda, Firecracker)
- Adding authentication before the analysis endpoint

## Project Structure

```
complex-code-test-dashboard/
├── app.py                      # Flask entry point
├── config.py                   # Configuration constants
├── requirements.txt
├── Procfile
├── render.yaml
├── backend/
│   ├── routes/
│   │   ├── analysis_routes.py  # POST /api/analyze, GET /api/results
│   │   └── report_routes.py    # GET /api/report/<id>
│   ├── analyzers/
│   │   ├── pytest_analyzer.py
│   │   ├── coverage_analyzer.py
│   │   ├── flake8_analyzer.py
│   │   ├── pylint_analyzer.py
│   │   ├── bandit_analyzer.py
│   │   └── pycodestyle_analyzer.py
│   ├── complexity/
│   │   └── complexity_analyzer.py   # Radon
│   ├── prediction/
│   │   └── defect_predictor.py      # Heuristic engine
│   ├── services/
│   │   ├── analysis_service.py      # Orchestration
│   │   ├── execution_service.py     # Safe subprocess runner
│   │   └── report_service.py        # JSON/HTML report generator
│   └── utils/
│       ├── validators.py
│       └── result_formatter.py
├── templates/
│   └── index.html
├── static/
│   ├── css/dashboard.css
│   ├── js/dashboard.js
│   └── samples/
│       ├── scientific_calculator.py
│       ├── bank_account.py
│       └── defective_code.py
└── tests/
    └── test_integration.py     # 15 test scenarios
```

## Defect Prediction Methodology

The defect risk score (0–100) is a **heuristic estimate**, not a machine-learning probability.

| Component | Weight | Description |
|-----------|--------|-------------|
| Security findings | 30% | Bandit HIGH/MEDIUM findings |
| Cyclomatic complexity | 25% | Average function complexity |
| Static analysis | 20% | Flake8 + Pylint findings count |
| Coverage deficit | 15% | 100% − average coverage |
| Style violations | 10% | Pycodestyle violation count |

Risk categories: LOW (0–24) · MODERATE (25–49) · HIGH (50–74) · CRITICAL (75–100)

## Academic Note

This project is submitted as a 7th-semester Software Testing coursework project. All tool integrations use real execution (subprocess calls to installed tools); no results are fabricated or hardcoded.
