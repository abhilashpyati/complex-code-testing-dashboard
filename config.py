"""
Configuration settings for the Complex Code Testing Dashboard.
"""
import os
import tempfile

# Flask settings
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"

# Analysis limits
MAX_CODE_SIZE_BYTES = 100_000       # 100 KB max source code
MAX_EXECUTION_TIMEOUT = 30          # seconds per tool
MAX_MEMORY_MB = 256
MAX_CONCURRENT_ANALYSES = 5

# In-memory result store lifetime (seconds)
RESULT_TTL_SECONDS = 3600           # 1 hour

# Temporary workspace
TEMP_DIR = tempfile.gettempdir()

# Cyclomatic complexity thresholds
COMPLEXITY_LOW_MAX = 5
COMPLEXITY_MODERATE_MAX = 12
COMPLEXITY_HIGH_MAX = 25

# Defect risk score weights (Phase 4: Coverage removed, redistributed to 100%)
RISK_WEIGHT_SECURITY = 0.353       # 35.3%
RISK_WEIGHT_COMPLEXITY = 0.294     # 29.4%
RISK_WEIGHT_STATIC = 0.235         # 23.5%
RISK_WEIGHT_STYLE = 0.118          # 11.8%

# Risk categories
RISK_CATEGORIES = {
    (0, 25): "LOW",
    (25, 50): "MODERATE",
    (50, 75): "HIGH",
    (75, 101): "CRITICAL",
}

# Supported sample programs
SAMPLE_NAMES = [
    "scientific_calculator",
    "bank_account",
    "defective_code",
]

# Deployment security note
SECURITY_WARNING = (
    "WARNING: Submitted code is executed in an isolated subprocess with "
    "timeout restrictions. Full sandboxing (seccomp, containers) is not "
    "available on standard Render free-tier deployments. Do not submit "
    "sensitive or malicious code."
)
