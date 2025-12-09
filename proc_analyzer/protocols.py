"""
Protocols (interfaces) pour les calculateurs de métriques.

Ces protocols définissent les interfaces communes pour les différents types
de calculateurs, permettant le polymorphisme sans héritage (composition).
"""

from typing import Protocol
from .parser import FunctionInfo


class ComplexityCalculator(Protocol):
    """
    Interface pour les calculateurs de complexité (cyclomatique, cognitive).
    
    Les calculateurs de complexité retournent un entier représentant
    la complexité d'une fonction.
    """
    
    def calculate(self, function: FunctionInfo) -> int:
        """
        Calcule la complexité d'une fonction.
        
        Args:
            function: Information sur la fonction à analyser
            
        Returns:
            Complexité (entier >= 0)
        """
        ...


class MetricsCalculator(Protocol):
    """
    Interface pour les calculateurs de métriques (Halstead, etc.).
    
    Les calculateurs de métriques retournent un objet de métriques
    avec plusieurs propriétés calculées.
    """
    
    def calculate(self, function: FunctionInfo) -> object:
        """
        Calcule les métriques d'une fonction.
        
        Args:
            function: Information sur la fonction à analyser
            
        Returns:
            Objet de métriques (typiquement une dataclass)
        """
        ...
