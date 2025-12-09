"""
Interface de base pour les formatters de rapports.
"""

from typing import Protocol
from pathlib import Path

from ..analyzer import AnalysisReport


class BaseFormatter(Protocol):
    """
    Interface pour les formatters de rapports d'analyse.
    
    Tous les formatters doivent implémenter ces méthodes pour générer
    les rapports dans différents formats.
    """
    
    def format(self, report: AnalysisReport) -> str:
        """
        Formate un rapport complet en chaîne de caractères.
        
        Args:
            report: Rapport d'analyse à formater
            
        Returns:
            Chaîne formatée du rapport
        """
        ...
    
    def save(self, report: AnalysisReport, output_path: str) -> None:
        """
        Sauvegarde un rapport formaté dans un fichier.
        
        Args:
            report: Rapport d'analyse à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        output = Path(output_path)
        output.write_text(self.format(report), encoding='utf-8')
