"""
Defective Code — Sample Program 3
Intentionally contains multiple categories of defects for demonstration.
"""
import os
import hashlib
import subprocess
from os import *  # noqa: F403,F401 — wildcard import (style violation)

PASSWORD = "admin123"   # hardcoded credential (security)
SECRET_KEY = "s3cr3t"   # hardcoded secret (security)

unused_variable = 42    # unused variable (static analysis)


def calculate_total(items):
    # Missing type hints, poor naming
    t = 0
    for i in items:
        for j in i:              # excessive nesting
            if j > 0:
                if j < 100:
                    if j != 50:  # deeply nested condition
                        t = t + j
    return t


def risky_eval(user_input):
    """Runs user input directly — dangerous eval usage."""
    result = eval(user_input)   # security: use of eval
    return result


def run_shell_command(cmd):
    """Runs a shell command without sanitisation."""
    output = subprocess.run(cmd, shell=True, capture_output=True)  # security: shell=True
    return output.stdout


def weak_hash(data):
    """Uses MD5 — weak cryptographic algorithm."""
    return hashlib.md5(data.encode()).hexdigest()   # security: weak hash


def divide(a, b):
    return a / b   # no ZeroDivisionError handling


def long_function_with_many_branches(x, y, z, w, v):
    """Overly complex function — high cyclomatic complexity."""
    result = 0
    if x > 0:
        result += x
    elif x < 0:
        result -= x
    else:
        result = 1

    if y > 10:
        if y > 100:
            result *= 2
        else:
            result += y
    elif y == 0:
        result = 0
    else:
        result -= y

    if z:
        for i in range(z):
            if i % 2 == 0:
                result += i
            else:
                result -= i

    if w is not None:
        if isinstance(w, list):
            for item in w:
                result += item
        elif isinstance(w, dict):
            for k, val in w.items():
                if val > 0:
                    result += val
        else:
            result += w

    if v > 0 and v < 10:
        result *= v
    elif v >= 10 and v < 100:
        result += v * 2
    elif v >= 100:
        result = result / v

    return result


def undeclared_reference():
    """References a variable that doesn't exist."""
    return undefined_var   # noqa: F821 — undefined variable


class PoorlyNamedClass:
    def __init__(self):
        self.x = 1
        self.y = 2
        self.z = 3

    def a(self):   # poor method name
        return self.x + self.y

    def b(self, n):   # poor method name, no docstring
        if n == 1:
            return self.x
        elif n == 2:
            return self.y
        elif n == 3:
            return self.z
        elif n == 4:
            return self.x + self.y + self.z
        else:
            return -1
