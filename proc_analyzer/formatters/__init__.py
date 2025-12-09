"""
Formatters pour les rapports d'analyse Pro*C.

Ce module fournit différents formats de sortie pour les rapports d'analyse :
- JSON (simple et pretty)
- HTML (rapport interactif)
- Markdown (compatible GitHub/GitLab)
"""

from .base import BaseFormatter
from .json_formatter import JSONFormatter
from .html_formatter import HTMLFormatter
from .markdown_formatter import MarkdownFormatter

__all__ = [
    'BaseFormatter',
    'JSONFormatter',
    'HTMLFormatter',
    'MarkdownFormatter',
]
