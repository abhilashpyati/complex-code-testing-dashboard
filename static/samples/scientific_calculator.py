"""
Scientific Calculator — Sample Program 1
A well-structured module for demonstrating testing scenarios.
"""
import math


class ScientificCalculator:
    """A scientific calculator with common mathematical operations."""

    def __init__(self):
        """Initialize calculator with empty history and zero last result."""
        self.history = []
        self.last_result = 0.0

    def add(self, a: float, b: float) -> float:
        """Add two numbers and record operation."""
        result = a + b
        self._record(f"{a} + {b} = {result}")
        self.last_result = result
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a and record operation."""
        result = a - b
        self._record(f"{a} - {b} = {result}")
        self.last_result = result
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers and record operation."""
        result = a * b
        self._record(f"{a} * {b} = {result}")
        self.last_result = result
        return result

    def divide(self, a: float, b: float) -> float:
        """Divide a by b; raise ZeroDivisionError if b is zero."""
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        result = a / b
        self._record(f"{a} / {b} = {result}")
        self.last_result = result
        return result

    def power(self, base: float, exp: float) -> float:
        """Compute base raised to the power of exp."""
        result = base ** exp
        self._record(f"{base} ^ {exp} = {result}")
        self.last_result = result
        return result

    def square_root(self, n: float) -> float:
        """Calculate square root; raise ValueError if n is negative."""
        if n < 0:
            raise ValueError("Cannot compute square root of a negative number")
        result = math.sqrt(n)
        self._record(f"sqrt({n}) = {result}")
        self.last_result = result
        return result

    def logarithm(self, n: float, base: float = math.e) -> float:
        """Compute logarithm of n to specified base."""
        if n <= 0:
            raise ValueError("Logarithm is only defined for positive numbers")
        if base <= 0 or base == 1:
            raise ValueError("Logarithm base must be positive and not equal to 1")
        result = math.log(n, base)
        self._record(f"log_{base}({n}) = {result}")
        self.last_result = result
        return result

    def sine(self, angle_degrees: float) -> float:
        """Calculate sine of an angle in degrees."""
        result = math.sin(math.radians(angle_degrees))
        self._record(f"sin({angle_degrees}°) = {result}")
        self.last_result = result
        return result

    def cosine(self, angle_degrees: float) -> float:
        """Calculate cosine of an angle in degrees."""
        result = math.cos(math.radians(angle_degrees))
        self._record(f"cos({angle_degrees}°) = {result}")
        self.last_result = result
        return result

    def tangent(self, angle_degrees: float) -> float:
        """Calculate tangent of an angle in degrees."""
        if angle_degrees % 180 == 90:
            raise ValueError("Tangent is undefined at 90 + 180k degrees")
        result = math.tan(math.radians(angle_degrees))
        self._record(f"tan({angle_degrees}°) = {result}")
        self.last_result = result
        return result

    def factorial(self, n: int) -> int:
        """Calculate factorial of non-negative integer n."""
        if not isinstance(n, int) or n < 0:
            raise ValueError("Factorial requires a non-negative integer")
        result = math.factorial(n)
        self._record(f"{n}! = {result}")
        self.last_result = result
        return result

    def clear_history(self):
        """Clear the history log of operations."""
        self.history = []

    def _record(self, operation: str):
        """Append operation string to execution history."""
        self.history.append(operation)


def compute_bmi(weight_kg: float, height_m: float) -> dict:
    """Calculate Body Mass Index and return category."""
    if weight_kg <= 0 or height_m <= 0:
        raise ValueError("Weight and height must be positive")
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25.0:
        category = "Normal"
    elif bmi < 30.0:
        category = "Overweight"
    else:
        category = "Obese"
    return {"bmi": round(bmi, 2), "category": category}
