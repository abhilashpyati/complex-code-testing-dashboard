# Complex Code Testing Dashboard

A professional, fully automated Python code quality and security analysis dashboard for a 7th-semester Software Testing academic project. Built with a clean, modern white-themed interface.

## Features & Analysis Architecture

The dashboard evaluates Python source code across **exactly 25 core test criteria** divided evenly (5 criteria each) across 5 primary analyzers, alongside an independent McCabe Cyclomatic Complexity module and a 4-factor heuristic Defect Risk Prediction engine.

| Group | Analyzer | Category | Criteria IDs | Description |
|---|---|---|---|---|
| Group 1 | PyTest | Dynamic Testing | `PT-01` – `PT-05` | Test discovery, assertion validation, runtime error detection, function execution, boundary testing |
| Group 2 | Flake8 | Static Analysis | `FL-01` – `FL-05` | Unused imports (F401), undefined names (F821), syntax issues (E999), wildcard imports (F403), general linting |
| Group 3 | Pylint | Code Quality | `PL-01` – `PL-05` | Naming conventions (C0103), unused symbols (W0612), error detection (E/F), warnings & docstrings (W/C), overall score (≥7.0) |
| Group 4 | Bandit | Security Analysis | `BD-01` – `BD-05` | Hardcoded credentials (B105), unsafe functions (eval/exec B307), weak crypto (B303), subprocess (B602), overall severity |
| Group 5 | Pycodestyle | Coding Standards | `PC-01` – `PC-05` | Indentation (E1xx), line length ≤120 (E501), whitespace (E2xx), blank lines (E3xx), general PEP 8 compliance |

### Independent Modules
- **Radon Complexity Analysis**: Evaluates McCabe Cyclomatic Complexity per function/method, assigns letter grades (A–F), detects hotspots, and calculates distribution (LOW, MODERATE, HIGH, CRITICAL).
- **Defect Risk Predictor**: Calculates a 0–100 heuristic risk score across 4 normalized dimensions with dynamic weight redistribution.

---

## Defect Risk Prediction Methodology

The defect risk score (0–100) is a **heuristic estimate** based on static code metrics, vulnerability scanning, and complexity measures:

| Component | Weight | Metric Source | Description |
|---|---|---|---|
| Security Findings | **35.3%** (`0.353`) | Bandit | Weighted count of HIGH (20 pts), MEDIUM (8 pts), and LOW (2 pts) vulnerabilities |
| Cyclomatic Complexity | **29.4%** (`0.294`) | Radon | Average cyclomatic complexity and presence of high-complexity hotspots |
| Static Code Analysis | **23.5%** (`0.235`) | Flake8 + Pylint | Syntax errors, undefined variables, naming violations, and code smells |
| Coding Style Compliance | **11.8%** (`0.118`) | Pycodestyle | PEP 8 adherence, line length, whitespace, and formatting violations |
| **Total** | **100.0%** (`1.000`) | | **Exact mathematical aggregate** |

> **Disclaimer:** *Defect risk is a heuristic estimate based on security, complexity, static analysis, and coding-style metrics. It does not guarantee the presence or absence of defects.*

---

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

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Running the Automated Test Suite

```bash
pytest tests/ -v --tb=short
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard UI (White Theme) |
| GET | `/api/health` | Service health check |
| POST | `/api/analyze` | Submit Python code for synchronous analysis (`{ "code": "...", "filename": "..." }`) |
| POST | `/api/analyze/upload` | Upload a `.py` file for analysis (`multipart/form-data`) |
| GET | `/api/results/<analysis_id>` | Retrieve in-memory analysis results by ID |
| GET | `/api/report/<analysis_id>?format=json` | Export JSON analysis report |
| GET | `/api/report/<analysis_id>?format=html` | Download self-contained HTML analysis report |
| GET | `/api/samples` | List preloaded sample programs (`bank_account`, `scientific_calculator`, `defective_code`) |

---

## Project Structure

```
complex-code-test-dashboard/
├── app.py                      # Flask entry point & CORS configuration
├── config.py                   # Global configuration & defect prediction weights
├── requirements.txt            # Python dependencies (coverage removed)
├── Procfile                    # Render web deployment command
├── render.yaml                 # Render blueprint
├── backend/
│   ├── routes/
│   │   ├── analysis_routes.py  # Analysis endpoints & sample loader
│   │   └── report_routes.py    # JSON & HTML report download routes
│   ├── analyzers/
│   │   ├── pytest_analyzer.py      # Group 1: Dynamic testing (PT-01 to PT-05)
│   │   ├── flake8_analyzer.py      # Group 2: Static analysis (FL-01 to FL-05)
│   │   ├── pylint_analyzer.py      # Group 3: Code quality (PL-01 to PL-05)
│   │   ├── bandit_analyzer.py      # Group 4: Security vulnerabilities (BD-01 to BD-05)
│   │   └── pycodestyle_analyzer.py # Group 5: PEP 8 standards (PC-01 to PC-05)
│   ├── complexity/
│   │   └── complexity_analyzer.py  # Independent Radon complexity module
│   ├── prediction/
│   │   └── defect_predictor.py     # 4-factor heuristic defect predictor
│   ├── services/
│   │   ├── analysis_service.py     # Orchestration & thread-safe in-memory store
│   │   ├── execution_service.py    # Isolated workspace & safe tool runner
│   │   └── report_service.py       # JSON/HTML report generators (white theme)
│   └── utils/
│       ├── validators.py           # AST syntax checking & input limits
│       └── result_formatter.py     # Criteria formatting & health score
├── templates/
│   └── index.html              # White-themed dashboard UI
├── static/
│   ├── css/dashboard.css       # Clean light styling & modern cards
│   ├── js/dashboard.js         # Reactive CodeMirror editor, Chart.js graphs, accordion
│   └── samples/
│       ├── scientific_calculator.py  # Fully documented math operations
│       ├── bank_account.py           # Fully documented banking transactions & loans
│       └── defective_code.py         # Known defect & security vulnerability sample
└── tests/
    └── test_integration.py     # Integration test suite validating all scenarios
```

---

## Academic Note

This project is submitted as a 7th-semester Software Testing coursework project. All tool integrations invoke actual command-line static analysis and dynamic testing utilities in isolated temporary environments; no analysis findings or scores are fabricated.
