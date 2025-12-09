"""
Formatter JSON pour les rapports d'analyse.
"""

import json
from datetime import datetime
from typing import Optional

from ..analyzer import AnalysisReport


class JSONFormatter:
    """
    Formatter pour générer des rapports au format JSON.
    
    Supporte deux modes :
    - Compact : pas d'indentation
    - Pretty : indentation pour lisibilité
    """
    
    def __init__(self, pretty: bool = True, indent: int = 2):
        """
        Initialise le formatter JSON.
        
        Args:
            pretty: Si True, utilise l'indentation pour un JSON lisible
            indent: Nombre d'espaces pour l'indentation (si pretty=True)
        """
        self.pretty = pretty
        self.indent = indent if pretty else None
    
    def format(self, report: AnalysisReport) -> str:
        """
        Formate un rapport en JSON.
        
        Args:
            report: Rapport d'analyse à formater
            
        Returns:
            Chaîne JSON formatée
        """
        data = {
            'metadata': {
                'version': '0.2.0',
                'generated_at': datetime.now().isoformat(),
                'tool': 'Pro*C Static Analyzer',
            },
            'report': report.to_dict(),
        }
        
        return json.dumps(data, indent=self.indent, ensure_ascii=False)
    
    def save(self, report: AnalysisReport, output_path: str) -> None:
        """
        Sauvegarde un rapport JSON dans un fichier.
        
        Args:
            report: Rapport d'analyse à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        from pathlib import Path
        output = Path(output_path)
        output.write_text(self.format(report), encoding='utf-8')
