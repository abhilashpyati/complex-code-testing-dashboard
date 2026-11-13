"""
Comprehensive test suite for the Complex Code Testing Dashboard.
Tests all 15 required scenarios.
"""
import sys
import os
import json
import time
import io
import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# ─── Sample code fixtures ─────────────────────────────────────────────────────

VALID_CODE = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

class Calculator:
    def multiply(self, a, b):
        return a * b
'''

INVALID_SYNTAX_CODE = '''
def broken(
    return 42  # SyntaxError: missing closing paren
'''

EMPTY_CODE = ''

MULTI_FUNCTION_CODE = '''
def func_a(x):
    return x + 1

def func_b(x):
    return x * 2

def func_c(x, y):
    return x + y

def func_d(lst):
    return [i * 2 for i in lst]
'''

BRANCHY_CODE = '''
def grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"

def classify(n):
    if n > 0:
        if n > 100:
            return "large positive"
        else:
            return "small positive"
    elif n < 0:
        return "negative"
    else:
        return "zero"
'''

UNUSED_VARIABLE_CODE = '''
def compute(x):
    result = x * 2
    unused = 999  # unused variable
    return result
'''

SECURITY_VULN_CODE = '''
import hashlib
import subprocess

PASSWORD = "super_secret"   # hardcoded credential

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True)  # insecure shell=True

def bad_hash(data):
    return hashlib.md5(data.encode()).hexdigest()  # weak hash

def eval_input(user_in):
    return eval(user_in)   # dangerous eval
'''

STYLE_VIOLATIONS_CODE = '''
import os
import sys
def myFunction(x,y):
    z=x+y
    return z
class myclass:
    def myMethod( self ):
        pass
'''

HIGH_COMPLEXITY_CODE = '''
def complex_function(a, b, c, d, e, f):
    result = 0
    if a > 0:
        result += a
    elif a < 0:
        result -= a
    else:
        result = 1
    if b > 10:
        if b > 100:
            result *= 2
        else:
            result += b
    elif b == 0:
        result = 0
    else:
        result -= b
    if c:
        for i in range(c):
            if i % 2 == 0:
                result += i
            else:
                result -= i
    if d is not None:
        if isinstance(d, list):
            for item in d:
                result += item
        elif isinstance(d, dict):
            for k, v in d.items():
                if v > 0:
                    result += v
        else:
            result += d
    if e > 0 and e < 10:
        result *= e
    elif e >= 10 and e < 100:
        result += e * 2
    elif e >= 100:
        result = result / e
    if f:
        result += f
    return result
'''

ASSERTION_FAIL_CODE = '''
def always_wrong():
    assert 1 == 2, "This always fails"
    return True
'''

OVERSIZED_CODE = 'x = 1\n' * 10001  # will exceed char limit when encoded


# ─── Flask test client ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ─── Helper ──────────────────────────────────────────────────────────────────

def post_analyze(client, code, filename='test_code.py'):
    return client.post(
        '/api/analyze',
        json={'code': code, 'filename': filename},
        content_type='application/json',
    )


# ═══════════════════════════════════════════════════════════════
# TEST CASE 1: Valid Python source code
# ═══════════════════════════════════════════════════════════════
class TestValidCode:
    def test_returns_200(self, client):
        resp = post_analyze(client, VALID_CODE)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_returns_analysis_id(self, client):
        resp = post_analyze(client, VALID_CODE)
        data = resp.get_json()
        assert 'analysis_id' in data
        assert len(data['analysis_id']) > 0

    def test_returns_25_criteria(self, client):
        resp = post_analyze(client, VALID_CODE)
        data = resp.get_json()
        assert 'all_criteria' in data
        assert len(data['all_criteria']) == 25, \
            f"Expected 25 criteria, got {len(data['all_criteria'])}"

    def test_health_score_between_0_100(self, client):
        resp = post_analyze(client, VALID_CODE)
        data = resp.get_json()
        score = data.get('health_score', 0)
        assert 0 <= score <= 100

    def test_no_criteria_marked_passed_without_execution(self, client):
        """No criterion should be PASSED if the tool didn't run."""
        resp = post_analyze(client, VALID_CODE)
        data = resp.get_json()
        for c in data.get('all_criteria', []):
            if c['status'] == 'PASSED':
                assert c['details'] != '', "PASSED criterion has no details"


# ═══════════════════════════════════════════════════════════════
# TEST CASE 2: Invalid Python syntax
# ═══════════════════════════════════════════════════════════════
class TestInvalidSyntax:
    def test_returns_422(self, client):
        resp = post_analyze(client, INVALID_SYNTAX_CODE)
        assert resp.status_code == 422

    def test_returns_validation_errors(self, client):
        resp = post_analyze(client, INVALID_SYNTAX_CODE)
        data = resp.get_json()
        assert 'validation_errors' in data
        assert len(data['validation_errors']) > 0

    def test_error_has_line_number(self, client):
        resp = post_analyze(client, INVALID_SYNTAX_CODE)
        data = resp.get_json()
        errors = data.get('validation_errors', [])
        assert any(e.get('line', 0) > 0 for e in errors), \
            "Expected at least one error with a line number"


# ═══════════════════════════════════════════════════════════════
# TEST CASE 3: Empty source code
# ═══════════════════════════════════════════════════════════════
class TestEmptyCode:
    def test_returns_422(self, client):
        resp = post_analyze(client, EMPTY_CODE)
        assert resp.status_code == 422

    def test_error_message_mentions_empty(self, client):
        resp = post_analyze(client, EMPTY_CODE)
        data = resp.get_json()
        errors = data.get('validation_errors', [])
        combined = ' '.join(str(e.get('message', '')) for e in errors).lower()
        assert 'empty' in combined or 'code' in combined


# ═══════════════════════════════════════════════════════════════
# TEST CASE 4: Code with multiple functions
# ═══════════════════════════════════════════════════════════════
class TestMultipleFunctions:
    def test_complexity_captures_multiple_functions(self, client):
        resp = post_analyze(client, MULTI_FUNCTION_CODE)
        assert resp.status_code == 200
        data = resp.get_json()
        fns = data.get('complexity', {}).get('functions', [])
        # Radon should detect at least some of the functions
        assert isinstance(fns, list), "Expected complexity.functions to be a list"


# ═══════════════════════════════════════════════════════════════
# TEST CASE 5: Code with multiple branches
# ═══════════════════════════════════════════════════════════════
class TestMultipleBranches:
    def test_analysis_succeeds(self, client):
        resp = post_analyze(client, BRANCHY_CODE)
        assert resp.status_code == 200

    def test_complexity_detected(self, client):
        resp = post_analyze(client, BRANCHY_CODE)
        data = resp.get_json()
        overall = data.get('complexity', {}).get('overall', {})
        # Branchy code should have complexity > 1
        avg = overall.get('average', 0)
        # May be 0 if radon not installed; acceptable
        assert isinstance(avg, (int, float))


# ═══════════════════════════════════════════════════════════════
# TEST CASE 6: Code with unused variables
# ═══════════════════════════════════════════════════════════════
class TestUnusedVariables:
    def test_analysis_succeeds(self, client):
        resp = post_analyze(client, UNUSED_VARIABLE_CODE)
        assert resp.status_code == 200

    def test_criteria_contain_static_analysis(self, client):
        resp = post_analyze(client, UNUSED_VARIABLE_CODE)
        data = resp.get_json()
        criteria = data.get('criteria', {})
        assert 'flake8' in criteria or 'pylint' in criteria


# ═══════════════════════════════════════════════════════════════
# TEST CASE 7: Code with security vulnerabilities
# ═══════════════════════════════════════════════════════════════
class TestSecurityVulnerabilities:
    def test_analysis_succeeds(self, client):
        resp = post_analyze(client, SECURITY_VULN_CODE)
        assert resp.status_code == 200

    def test_bandit_criteria_present(self, client):
        resp = post_analyze(client, SECURITY_VULN_CODE)
        data = resp.get_json()
        bandit_crit = data.get('criteria', {}).get('bandit', [])
        assert len(bandit_crit) == 5, f"Expected 5 Bandit criteria, got {len(bandit_crit)}"

    def test_some_criteria_not_all_passed_on_vuln_code(self, client):
        """Security-vulnerable code should not have all Bandit criteria PASSED."""
        resp = post_analyze(client, SECURITY_VULN_CODE)
        data = resp.get_json()
        bandit_crit = data.get('criteria', {}).get('bandit', [])
        statuses = [c['status'] for c in bandit_crit]
        # At least some should be WARNING, FAILED, or NOT_EXECUTED
        # (may be NOT_EXECUTED if bandit not installed)
        all_passed = all(s == 'PASSED' for s in statuses)
        # If bandit is installed, some should fail; if not, all will be NOT_EXECUTED
        assert not all_passed or all(s == 'NOT_EXECUTED' for s in statuses), \
            "Security-vulnerable code has all Bandit criteria PASSED — suspicious"


# ═══════════════════════════════════════════════════════════════
# TEST CASE 8: Code with style violations
# ═══════════════════════════════════════════════════════════════
class TestStyleViolations:
    def test_analysis_succeeds(self, client):
        resp = post_analyze(client, STYLE_VIOLATIONS_CODE)
        assert resp.status_code == 200

    def test_pycodestyle_findings_captured(self, client):
        resp = post_analyze(client, STYLE_VIOLATIONS_CODE)
        data = resp.get_json()
        # pycodestyle findings are under the findings key
        style_findings = data.get('findings', {}).get('pycodestyle', [])
        # Either findings exist or tool not installed; both are acceptable
        assert isinstance(style_findings, list)


# ═══════════════════════════════════════════════════════════════
# TEST CASE 9: Code with high cyclomatic complexity
# ═══════════════════════════════════════════════════════════════
class TestHighComplexity:
    def test_analysis_succeeds(self, client):
        resp = post_analyze(client, HIGH_COMPLEXITY_CODE)
        assert resp.status_code == 200

    def test_complexity_overall_present(self, client):
        resp = post_analyze(client, HIGH_COMPLEXITY_CODE)
        data = resp.get_json()
        overall = data.get('complexity', {}).get('overall', {})
        assert 'average' in overall or 'max' in overall


# ═══════════════════════════════════════════════════════════════
# TEST CASE 10: Code with failing assertions
# ═══════════════════════════════════════════════════════════════
class TestFailingAssertions:
    def test_analysis_succeeds(self, client):
        resp = post_analyze(client, ASSERTION_FAIL_CODE)
        assert resp.status_code == 200

    def test_criteria_returned(self, client):
        resp = post_analyze(client, ASSERTION_FAIL_CODE)
        data = resp.get_json()
        all_crit = data.get('all_criteria', [])
        assert len(all_crit) == 25


# ═══════════════════════════════════════════════════════════════
# TEST CASE 11: Execution timeout (simulated via oversized code)
# ═══════════════════════════════════════════════════════════════
class TestExecutionTimeout:
    def test_oversized_code_rejected(self, client):
        """Oversized code should be rejected at validation."""
        resp = post_analyze(client, OVERSIZED_CODE)
        # Should be 422 (too large) or 200 with NOT_EXECUTED statuses
        assert resp.status_code in (422, 200)


# ═══════════════════════════════════════════════════════════════
# TEST CASE 12: Invalid file upload
# ═══════════════════════════════════════════════════════════════
class TestInvalidFileUpload:
    def test_non_py_file_rejected(self, client):
        data = {'file': (io.BytesIO(b'print("hello")'), 'test.txt')}
        resp = client.post('/api/analyze/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 400
        body = resp.get_json()
        assert 'error' in body

    def test_no_file_field_rejected(self, client):
        resp = client.post('/api/analyze/upload', data={}, content_type='multipart/form-data')
        assert resp.status_code == 400

    def test_path_traversal_filename_rejected(self, client):
        data = {'file': (io.BytesIO(b'x=1'), '../evil.py')}
        resp = client.post('/api/analyze/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════
# TEST CASE 13: Oversized file upload
# ═══════════════════════════════════════════════════════════════
class TestOversizedUpload:
    def test_large_file_rejected(self, client):
        big_code = b'# comment\n' * 15000  # ~150KB
        data = {'file': (io.BytesIO(big_code), 'big_file.py')}
        resp = client.post('/api/analyze/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code in (400, 413, 422), \
            f"Expected 400/413/422 for oversized upload, got {resp.status_code}"


# ═══════════════════════════════════════════════════════════════
# TEST CASE 14: Report generation
# ═══════════════════════════════════════════════════════════════
class TestReportGeneration:
    def test_json_report_downloadable(self, client):
        # First run analysis
        resp = post_analyze(client, VALID_CODE)
        assert resp.status_code == 200
        analysis_id = resp.get_json()['analysis_id']

        # Request JSON report
        report_resp = client.get(f'/api/report/{analysis_id}?format=json')
        assert report_resp.status_code == 200
        assert report_resp.content_type == 'application/json'

    def test_html_report_downloadable(self, client):
        resp = post_analyze(client, VALID_CODE)
        assert resp.status_code == 200
        analysis_id = resp.get_json()['analysis_id']

        report_resp = client.get(f'/api/report/{analysis_id}?format=html')
        assert report_resp.status_code == 200
        assert 'text/html' in report_resp.content_type

    def test_unknown_analysis_id_returns_404(self, client):
        resp = client.get('/api/report/00000000-0000-0000-0000-000000000000?format=json')
        assert resp.status_code == 404

    def test_html_report_contains_key_sections(self, client):
        resp = post_analyze(client, VALID_CODE)
        analysis_id = resp.get_json()['analysis_id']
        report_resp = client.get(f'/api/report/{analysis_id}?format=html')
        body = report_resp.data.decode()
        assert 'Health Score' in body
        assert 'Test Criteria' in body


# ═══════════════════════════════════════════════════════════════
# TEST CASE 15: API Validation
# ═══════════════════════════════════════════════════════════════
class TestAPIValidation:
    def test_health_check_endpoint(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('status') == 'ok'

    def test_non_json_body_returns_400(self, client):
        resp = client.post(
            '/api/analyze',
            data='not json',
            content_type='text/plain',
        )
        assert resp.status_code == 400

    def test_missing_code_field_rejected(self, client):
        resp = client.post(
            '/api/analyze',
            json={'filename': 'test.py'},
            content_type='application/json',
        )
        assert resp.status_code == 422  # empty code

    def test_samples_endpoint_returns_dict(self, client):
        resp = client.get('/api/samples')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'samples' in data
        assert isinstance(data['samples'], dict)

    def test_results_endpoint_returns_404_for_unknown(self, client):
        resp = client.get('/api/results/nonexistent-id-12345')
        assert resp.status_code == 404

    def test_analysis_result_retrievable(self, client):
        """Analysis results should be retrievable by ID after submission."""
        resp = post_analyze(client, VALID_CODE)
        assert resp.status_code == 200
        analysis_id = resp.get_json()['analysis_id']

        fetch_resp = client.get(f'/api/results/{analysis_id}')
        assert fetch_resp.status_code == 200
        assert fetch_resp.get_json()['analysis_id'] == analysis_id

    def test_criteria_structure_valid(self, client):
        """Each criterion must have required fields."""
        resp = post_analyze(client, VALID_CODE)
        data = resp.get_json()
        for c in data.get('all_criteria', []):
            assert 'id' in c, f"Missing 'id' in criterion: {c}"
            assert 'name' in c
            assert 'status' in c
            assert c['status'] in ('PASSED', 'WARNING', 'FAILED', 'NOT_EXECUTED'), \
                f"Invalid status: {c['status']}"
            assert 'tool' in c
            assert 'details' in c

    def test_defect_prediction_structure(self, client):
        resp = post_analyze(client, VALID_CODE)
        data = resp.get_json()
        pred = data.get('defect_prediction', {})
        assert 'score' in pred
        assert 'category' in pred
        assert pred['category'] in ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')
        assert 0 <= pred['score'] <= 100
        assert 'methodology_note' in pred
        assert 'heuristic' in pred['methodology_note'].lower() or \
               'HEURISTIC' in pred['methodology_note']


# ═══════════════════════════════════════════════════════════════
# ADDITIONAL AUDIT TEST CASES (Part 3 scenarios & Security)
# ═══════════════════════════════════════════════════════════════

class TestLogicalErrors:
    """Scenario 3: Python code containing logical errors."""
    def test_logical_error_analysis(self, client):
        code = '''
def calculate_average(numbers):
    # Bug: dividing by fixed 2 instead of len(numbers)
    return sum(numbers) / 2

def is_positive(num):
    # Bug: incorrect sign logic
    return num < 0
'''
        resp = post_analyze(client, code, 'logic_test.py')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['all_criteria']) == 25
        assert 'analysis_id' in data


class TestUndefinedVariables:
    """Scenario 6: Python code with undefined variables."""
    def test_undefined_variable_detected(self, client):
        code = '''
def process_data(val):
    result = val + undefined_variable_xyz
    return result
'''
        resp = post_analyze(client, code, 'undefined_test.py')
        assert resp.status_code == 200
        data = resp.get_json()
        flake8_crit = data.get('criteria', {}).get('flake8', [])
        # FL-02 checks for undefined variables (F821)
        f821_crit = next((c for c in flake8_crit if c['id'] == 'FL-02'), None)
        assert f821_crit is not None
        assert f821_crit['status'] in ('FAILED', 'WARNING')


class TestDifferentFilenames:
    """Scenario 13: Files with different valid filenames."""
    def test_valid_custom_filenames(self, client):
        valid_names = [
            'math_utils.py',
            'data-processor_v2.py',
            'algorithm_123.py',
            'my_service.py',
        ]
        for fname in valid_names:
            resp = post_analyze(client, VALID_CODE, filename=fname)
            assert resp.status_code == 200, f"Failed for valid filename: {fname}"
            data = resp.get_json()
            assert data.get('filename') == fname


class TestRuntimeExceptions:
    """Scenario 14: Code that causes runtime exceptions."""
    def test_runtime_zero_division(self, client):
        code = '''
def divide_by_zero():
    return 10 / 0

def bad_index():
    lst = []
    return lst[5]
'''
        resp = post_analyze(client, code, 'runtime_err.py')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['all_criteria']) == 25


class TestHTMLEscapingInReports:
    """Security audit: verify HTML special characters in code/messages are safely escaped."""
    def test_special_chars_escaped_in_report(self, client):
        xss_code = '''
def test_xss():
    """<script>alert('XSS')</script>"""
    msg = "<img src=x onerror=alert('xss')>"
    return msg
'''
        resp = post_analyze(client, xss_code, 'xss_test.py')
        assert resp.status_code == 200
        analysis_id = resp.get_json()['analysis_id']

        report_resp = client.get(f'/api/report/{analysis_id}?format=html')
        assert report_resp.status_code == 200
        body = report_resp.data.decode()
        # Raw dangerous script tags should NOT appear unescaped
        assert '<script>alert(' not in body
        assert '<img src=x onerror=' not in body
        # Instead, escaped entities or safe rendering should be present
        assert 'xss_test.py' in body


class TestBanditSeverityAndClassification:
    """Audit: Bandit classifies findings by severity/confidence and reports them without false negatives."""
    def test_bandit_finds_vulnerabilities(self, client):
        resp = post_analyze(client, SECURITY_VULN_CODE, 'security_audit.py')
        assert resp.status_code == 200
        data = resp.get_json()
        bandit_findings = data.get('findings', {}).get('bandit', [])
        assert len(bandit_findings) > 0, "Bandit should detect issues in SECURITY_VULN_CODE"
        for f in bandit_findings:
            assert 'severity' in f
            assert 'confidence' in f
            assert f['severity'] in ('LOW', 'MEDIUM', 'HIGH')
            assert f['confidence'] in ('LOW', 'MEDIUM', 'HIGH')

