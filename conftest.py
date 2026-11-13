"""
pytest configuration — adds project root to sys.path.
"""
import sys
import os

# Ensure project root is in path for all tests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
