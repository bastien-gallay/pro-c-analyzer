"""
Préprocesseur Pro*C
Neutralise les blocs EXEC SQL pour permettre le parsing C standard
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ExecSqlBlock:
    """Représente un bloc EXEC SQL trouvé dans le code"""
    start: int          # Position de début dans le source original
    end: int            # Position de fin
    line_number: int    # Numéro de ligne
    content: str        # Contenu du bloc
    sql_type: str       # Type: SELECT, INSERT, UPDATE, DELETE, DECLARE, etc.


class ProCPreprocessor:
    """
    Préprocesseur pour code Pro*C.
    Remplace les blocs EXEC SQL par des appels de fonction factices
    pour permettre le parsing par un parser C standard.
    """
    
    # Pattern pour détecter les blocs EXEC SQL
    # Gère les blocs multi-lignes et les différentes variantes
    EXEC_SQL_PATTERN = re.compile(
        r'EXEC\s+SQL\s+(.*?)\s*;',
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern pour EXEC ORACLE
    EXEC_ORACLE_PATTERN = re.compile(
        r'EXEC\s+ORACLE\s+(.*?)\s*;',
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern pour les déclarations de variables hôtes
    # EXEC SQL BEGIN DECLARE SECTION / END DECLARE SECTION
    DECLARE_SECTION_PATTERN = re.compile(
        r'EXEC\s+SQL\s+BEGIN\s+DECLARE\s+SECTION\s*;(.*?)EXEC\s+SQL\s+END\s+DECLARE\s+SECTION\s*;',
        re.IGNORECASE | re.DOTALL
    )
    
    # Types SQL reconnus pour classification
    SQL_TYPES = {
        'SELECT': re.compile(r'^\s*SELECT\b', re.IGNORECASE),
        'INSERT': re.compile(r'^\s*INSERT\b', re.IGNORECASE),
        'UPDATE': re.compile(r'^\s*UPDATE\b', re.IGNORECASE),
        'DELETE': re.compile(r'^\s*DELETE\b', re.IGNORECASE),
        'DECLARE': re.compile(r'^\s*(BEGIN\s+)?DECLARE\b', re.IGNORECASE),
        'CURSOR': re.compile(r'^\s*DECLARE\s+\w+\s+CURSOR\b', re.IGNORECASE),
        'OPEN': re.compile(r'^\s*OPEN\b', re.IGNORECASE),
        'CLOSE': re.compile(r'^\s*CLOSE\b', re.IGNORECASE),
        'FETCH': re.compile(r'^\s*FETCH\b', re.IGNORECASE),
        'COMMIT': re.compile(r'^\s*COMMIT\b', re.IGNORECASE),
        'ROLLBACK': re.compile(r'^\s*ROLLBACK\b', re.IGNORECASE),
        'CONNECT': re.compile(r'^\s*CONNECT\b', re.IGNORECASE),
        'INCLUDE': re.compile(r'^\s*INCLUDE\b', re.IGNORECASE),
        'WHENEVER': re.compile(r'^\s*WHENEVER\b', re.IGNORECASE),
        'EXECUTE': re.compile(r'^\s*EXECUTE\b', re.IGNORECASE),
        'PREPARE': re.compile(r'^\s*PREPARE\b', re.IGNORECASE),
        'CALL': re.compile(r'^\s*CALL\b', re.IGNORECASE),
    }
    
    def __init__(self) -> None:
        self.sql_blocks: List[ExecSqlBlock] = []
        self._line_offsets: List[int] = []
    
    def _compute_line_offsets(self, source: str) -> None:
        """Calcule les offsets de chaque ligne pour conversion position -> ligne"""
        self._line_offsets = [0]
        for i, char in enumerate(source):
            if char == '\n':
                self._line_offsets.append(i + 1)
    
    def _position_to_line(self, position: int) -> int:
        """Convertit une position dans le source en numéro de ligne (1-indexed)"""
        for i, offset in enumerate(self._line_offsets):
            if offset > position:
                return i
        return len(self._line_offsets)
    
    def _classify_sql(self, content: str) -> str:
        """Identifie le type d'instruction SQL"""
        for sql_type, pattern in self.SQL_TYPES.items():
            if pattern.match(content):
                return sql_type
        return 'OTHER'
    
    def preprocess(self, source: str) -> Tuple[str, List[ExecSqlBlock]]:
        """
        Prétraite le code Pro*C.
        
        Args:
            source: Code source Pro*C
            
        Returns:
            Tuple (code_c_pur, liste_blocs_sql)
        """
        self.sql_blocks = []
        self._compute_line_offsets(source)
        
        result = source
        offset_adjustment = 0
        
        # D'abord, traiter les sections DECLARE (les garder comme commentaires)
        for match in self.DECLARE_SECTION_PATTERN.finditer(source):
            block = ExecSqlBlock(
                start=match.start(),
                end=match.end(),
                line_number=self._position_to_line(match.start()),
                content=match.group(0),
                sql_type='DECLARE_SECTION'
            )
            self.sql_blocks.append(block)
        
        # Remplacer les DECLARE SECTIONS par des commentaires
        result = self.DECLARE_SECTION_PATTERN.sub(
            lambda m: f'/* EXEC SQL DECLARE SECTION */\n{m.group(1)}\n/* END DECLARE SECTION */',
            result
        )
        
        # Recalculer les offsets après modification
        self._compute_line_offsets(result)
        
        # Traiter les blocs EXEC SQL restants
        processed = []
        last_end = 0
        
        for match in self.EXEC_SQL_PATTERN.finditer(result):
            # Vérifier qu'on n'est pas dans une section déjà traitée
            sql_content = match.group(1).strip()
            if sql_content.upper().startswith('BEGIN DECLARE') or sql_content.upper().startswith('END DECLARE'):
                continue
                
            block = ExecSqlBlock(
                start=match.start(),
                end=match.end(),
                line_number=self._position_to_line(match.start()),
                content=match.group(0),
                sql_type=self._classify_sql(sql_content)
            )
            self.sql_blocks.append(block)
            
            # Construire le remplacement
            # On utilise un appel de fonction factice pour préserver la structure
            replacement = f'__exec_sql_{block.sql_type.lower()}__()'
            
            processed.append(result[last_end:match.start()])
            processed.append(replacement)
            last_end = match.end()
        
        processed.append(result[last_end:])
        result = ''.join(processed)
        
        # Traiter aussi EXEC ORACLE
        result = self.EXEC_ORACLE_PATTERN.sub('__exec_oracle__()', result)
        
        return result, self.sql_blocks
    
    def get_sql_statistics(self) -> dict:
        """Retourne des statistiques sur les blocs SQL trouvés"""
        stats = {
            'total_blocks': len(self.sql_blocks),
            'by_type': {},
        }
        
        for block in self.sql_blocks:
            sql_type = block.sql_type
            if sql_type not in stats['by_type']:
                stats['by_type'][sql_type] = 0
            stats['by_type'][sql_type] += 1
        
        return stats


def preprocess_file(filepath: str) -> Tuple[str, List[ExecSqlBlock]]:
    """
    Fonction utilitaire pour prétraiter un fichier Pro*C.
    
    Args:
        filepath: Chemin vers le fichier .pc
        
    Returns:
        Tuple (code_c_pur, liste_blocs_sql)
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()
    
    preprocessor = ProCPreprocessor()
    return preprocessor.preprocess(source)
