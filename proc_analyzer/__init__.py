"""
Pro*C Static Analyzer
Analyseur statique pour code Pro*C (Oracle embedded SQL in C)
"""

__version__ = "0.2.0"
__author__ = "Bastien"

from .analyzer import ProCAnalyzer
from .cognitive import CognitiveCalculator
from .comments import CommentAnalyzer, ModuleInfo, ModuleInventory, TodoItem
from .cursors import CursorAnalysisResult, CursorAnalyzer
from .cyclomatic import CyclomaticCalculator
from .halstead import HalsteadCalculator, HalsteadMetrics
from .memory import MemoryAnalysisResult, MemoryAnalyzer
from .preprocessor import ProCPreprocessor

__all__ = [
    "ProCAnalyzer",
    "ProCPreprocessor",
    "CyclomaticCalculator",
    "CognitiveCalculator",
    "HalsteadCalculator",
    "HalsteadMetrics",
    "CommentAnalyzer",
    "TodoItem",
    "ModuleInfo",
    "ModuleInventory",
    "CursorAnalyzer",
    "CursorAnalysisResult",
    "MemoryAnalyzer",
    "MemoryAnalysisResult",
]
