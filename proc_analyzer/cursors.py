"""
Analyseur de curseurs SQL Pro*C

Détecte:
- Curseurs déclarés
- Curseurs imbriqués (ouverture dans une boucle de fetch)
- Curseurs non fermés
- Patterns de curseurs problématiques
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum

from .utils import get_line_number_from_position


class CursorIssueType(Enum):
    """Types de problèmes de curseurs"""
    NESTED_CURSOR = "nested_cursor"           # Curseur dans boucle de fetch
    UNCLOSED_CURSOR = "unclosed_cursor"       # Curseur ouvert mais pas fermé
    FETCH_WITHOUT_CHECK = "fetch_no_check"    # FETCH sans vérification SQLCODE
    REOPEN_WITHOUT_CLOSE = "reopen_no_close"  # OPEN sans CLOSE préalable
    CURSOR_IN_LOOP = "cursor_in_loop"         # DECLARE dans une boucle


@dataclass
class CursorInfo:
    """Information sur un curseur SQL"""
    name: str
    declare_line: int
    select_statement: str = ""
    is_dynamic: bool = False
    
    # Localisations
    open_lines: List[int] = field(default_factory=list)
    fetch_lines: List[int] = field(default_factory=list)
    close_lines: List[int] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'declare_line': self.declare_line,
            'is_dynamic': self.is_dynamic,
            'open_count': len(self.open_lines),
            'fetch_count': len(self.fetch_lines),
            'close_count': len(self.close_lines),
            'open_lines': self.open_lines,
            'close_lines': self.close_lines,
        }


@dataclass
class CursorIssue:
    """Un problème détecté sur un curseur"""
    cursor_name: str
    issue_type: CursorIssueType
    line_number: int
    message: str
    severity: str  # error, warning, info
    
    def to_dict(self) -> dict:
        return {
            'cursor_name': self.cursor_name,
            'issue_type': self.issue_type.value,
            'line_number': self.line_number,
            'message': self.message,
            'severity': self.severity,
        }


@dataclass
class CursorAnalysisResult:
    """Résultat de l'analyse des curseurs"""
    cursors: List[CursorInfo] = field(default_factory=list)
    issues: List[CursorIssue] = field(default_factory=list)
    nested_cursor_count: int = 0
    
    @property
    def total_cursors(self) -> int:
        return len(self.cursors)
    
    @property
    def total_issues(self) -> int:
        return len(self.issues)
    
    @property
    def issues_by_severity(self) -> Dict[str, int]:
        counts = {'error': 0, 'warning': 0, 'info': 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts
    
    def to_dict(self) -> dict:
        return {
            'total_cursors': self.total_cursors,
            'total_issues': self.total_issues,
            'nested_cursor_count': self.nested_cursor_count,
            'issues_by_severity': self.issues_by_severity,
            'cursors': [c.to_dict() for c in self.cursors],
            'issues': [i.to_dict() for i in self.issues],
        }


class CursorAnalyzer:
    """
    Analyse les curseurs SQL dans du code Pro*C.
    """
    
    # Patterns pour détecter les opérations sur curseurs
    DECLARE_CURSOR = re.compile(
        r'EXEC\s+SQL\s+DECLARE\s+(\w+)\s+CURSOR\s+FOR\s+(.*?);',
        re.IGNORECASE | re.DOTALL
    )
    
    OPEN_CURSOR = re.compile(
        r'EXEC\s+SQL\s+OPEN\s+(\w+)',
        re.IGNORECASE
    )
    
    FETCH_CURSOR = re.compile(
        r'EXEC\s+SQL\s+FETCH\s+(\w+)',
        re.IGNORECASE
    )
    
    CLOSE_CURSOR = re.compile(
        r'EXEC\s+SQL\s+CLOSE\s+(\w+)',
        re.IGNORECASE
    )
    
    # Pattern pour curseurs dynamiques
    PREPARE_STMT = re.compile(
        r'EXEC\s+SQL\s+PREPARE\s+(\w+)\s+FROM',
        re.IGNORECASE
    )
    
    DECLARE_DYNAMIC = re.compile(
        r'EXEC\s+SQL\s+DECLARE\s+(\w+)\s+CURSOR\s+FOR\s+(\w+)',
        re.IGNORECASE
    )
    
    # Patterns pour détecter les boucles
    LOOP_PATTERNS = [
        re.compile(r'\bwhile\s*\(', re.IGNORECASE),
        re.compile(r'\bfor\s*\(', re.IGNORECASE),
        re.compile(r'\bdo\s*\{', re.IGNORECASE),
    ]
    
    # Pattern pour vérification SQLCODE après FETCH
    SQLCODE_CHECK = re.compile(
        r'(sqlca\.sqlcode|SQLCODE)\s*(==|!=|<|>|<=|>=)',
        re.IGNORECASE
    )
    
    def __init__(self) -> None:
        self.result = CursorAnalysisResult()
        self._cursor_map: Dict[str, CursorInfo] = {}
        self._prepared_stmts: Set[str] = set()
        self._lines: List[str] = []
    
    def analyze(self, source: str) -> CursorAnalysisResult:
        """
        Analyse les curseurs dans le code source.
        
        Args:
            source: Code source Pro*C
            
        Returns:
            Résultat de l'analyse
        """
        self.result = CursorAnalysisResult()
        self._cursor_map = {}
        self._prepared_stmts = set()
        self._lines = source.split('\n')
        
        # 1. Trouver les PREPARE (pour curseurs dynamiques)
        self._find_prepared_statements(source)
        
        # 2. Trouver les DECLARE CURSOR
        self._find_cursor_declarations(source)
        
        # 3. Trouver les OPEN/FETCH/CLOSE
        self._find_cursor_operations(source)
        
        # 4. Analyser les problèmes
        self._analyze_issues(source)
        
        self.result.cursors = list(self._cursor_map.values())
        return self.result
    
    
    def _find_prepared_statements(self, source: str) -> None:
        """Trouve les statements préparés"""
        for match in self.PREPARE_STMT.finditer(source):
            stmt_name = match.group(1).lower()
            self._prepared_stmts.add(stmt_name)
    
    def _find_cursor_declarations(self, source: str) -> None:
        """Trouve les déclarations de curseurs"""
        # Curseurs statiques
        for match in self.DECLARE_CURSOR.finditer(source):
            cursor_name = match.group(1).lower()
            select_stmt = match.group(2).strip()
            line_num = get_line_number_from_position(source, match.start())
            
            cursor = CursorInfo(
                name=cursor_name,
                declare_line=line_num,
                select_statement=select_stmt,
                is_dynamic=False,
            )
            self._cursor_map[cursor_name] = cursor
        
        # Curseurs dynamiques
        for match in self.DECLARE_DYNAMIC.finditer(source):
            cursor_name = match.group(1).lower()
            stmt_name = match.group(2).lower()
            line_num = get_line_number_from_position(source, match.start())
            
            if stmt_name in self._prepared_stmts:
                cursor = CursorInfo(
                    name=cursor_name,
                    declare_line=line_num,
                    is_dynamic=True,
                )
                self._cursor_map[cursor_name] = cursor
    
    def _find_cursor_operations(self, source: str) -> None:
        """Trouve les opérations OPEN/FETCH/CLOSE"""
        # OPEN
        for match in self.OPEN_CURSOR.finditer(source):
            cursor_name = match.group(1).lower()
            line_num = get_line_number_from_position(source, match.start())
            
            if cursor_name in self._cursor_map:
                self._cursor_map[cursor_name].open_lines.append(line_num)
        
        # FETCH
        for match in self.FETCH_CURSOR.finditer(source):
            cursor_name = match.group(1).lower()
            line_num = get_line_number_from_position(source, match.start())
            
            if cursor_name in self._cursor_map:
                self._cursor_map[cursor_name].fetch_lines.append(line_num)
        
        # CLOSE
        for match in self.CLOSE_CURSOR.finditer(source):
            cursor_name = match.group(1).lower()
            line_num = get_line_number_from_position(source, match.start())
            
            if cursor_name in self._cursor_map:
                self._cursor_map[cursor_name].close_lines.append(line_num)
    
    def _analyze_issues(self, source: str) -> None:
        """Analyse les problèmes potentiels"""
        
        for cursor_name, cursor in self._cursor_map.items():
            # Curseur non fermé
            if cursor.open_lines and not cursor.close_lines:
                self.result.issues.append(CursorIssue(
                    cursor_name=cursor_name,
                    issue_type=CursorIssueType.UNCLOSED_CURSOR,
                    line_number=cursor.open_lines[0],
                    message=f"Curseur '{cursor_name}' ouvert ligne {cursor.open_lines[0]} mais jamais fermé",
                    severity='warning',
                ))
            
            # Plus d'OPEN que de CLOSE
            if len(cursor.open_lines) > len(cursor.close_lines):
                self.result.issues.append(CursorIssue(
                    cursor_name=cursor_name,
                    issue_type=CursorIssueType.REOPEN_WITHOUT_CLOSE,
                    line_number=cursor.open_lines[-1],
                    message=f"Curseur '{cursor_name}': {len(cursor.open_lines)} OPEN pour {len(cursor.close_lines)} CLOSE",
                    severity='warning',
                ))
        
        # Détecter les curseurs imbriqués
        self._detect_nested_cursors(source)
        
        # Détecter FETCH sans vérification
        self._detect_unchecked_fetch(source)
    
    def _detect_nested_cursors(self, source: str) -> None:
        """Détecte les curseurs ouverts dans une boucle de FETCH"""
        
        # Trouver les zones de boucle FETCH
        fetch_loops = self._find_fetch_loops(source)
        
        for loop_start, loop_end, outer_cursor in fetch_loops:
            # Chercher des OPEN dans cette zone
            loop_content = source[loop_start:loop_end]
            
            for match in self.OPEN_CURSOR.finditer(loop_content):
                inner_cursor = match.group(1).lower()
                if inner_cursor != outer_cursor:
                    abs_pos = loop_start + match.start()
                    line_num = get_line_number_from_position(source, abs_pos)
                    
                    self.result.issues.append(CursorIssue(
                        cursor_name=inner_cursor,
                        issue_type=CursorIssueType.NESTED_CURSOR,
                        line_number=line_num,
                        message=f"Curseur '{inner_cursor}' ouvert dans la boucle FETCH de '{outer_cursor}' - risque de performance",
                        severity='error',
                    ))
                    self.result.nested_cursor_count += 1
    
    def _find_fetch_loops(self, source: str) -> List[Tuple[int, int, str]]:
        """
        Trouve les boucles contenant des FETCH.
        Retourne: [(start, end, cursor_name), ...]
        """
        results = []
        
        # Chercher les patterns while(1) { ... FETCH ... }
        # Simplification: on cherche les FETCH et on identifie leur boucle englobante
        
        for match in self.FETCH_CURSOR.finditer(source):
            cursor_name = match.group(1).lower()
            fetch_pos = match.start()
            
            # Chercher la boucle englobante
            loop_info = self._find_enclosing_loop(source, fetch_pos)
            if loop_info:
                results.append((loop_info[0], loop_info[1], cursor_name))
        
        return results
    
    def _find_enclosing_loop(self, source: str, pos: int) -> Optional[Tuple[int, int]]:
        """
        Trouve la boucle englobant une position.
        Retourne (start, end) ou None.
        """
        # Recherche simplifiée: remonter pour trouver while/for/do
        search_start = max(0, pos - 2000)  # Limiter la recherche
        preceding = source[search_start:pos]
        
        # Chercher le dernier while/for/do
        best_match = None
        best_pos = -1
        
        for pattern in self.LOOP_PATTERNS:
            for match in pattern.finditer(preceding):
                if match.start() > best_pos:
                    best_pos = match.start()
                    best_match = match
        
        if best_match is None:
            return None
        
        # Trouver la fin de la boucle (accolade fermante correspondante)
        loop_start = search_start + best_pos
        
        # Compter les accolades
        brace_count = 0
        in_loop = False
        loop_end = len(source)
        
        for i, char in enumerate(source[loop_start:], start=loop_start):
            if char == '{':
                brace_count += 1
                in_loop = True
            elif char == '}':
                brace_count -= 1
                if in_loop and brace_count == 0:
                    loop_end = i
                    break
        
        return (loop_start, loop_end)
    
    def _detect_unchecked_fetch(self, source: str) -> None:
        """Détecte les FETCH sans vérification immédiate de SQLCODE"""
        
        for match in self.FETCH_CURSOR.finditer(source):
            cursor_name = match.group(1).lower()
            fetch_end = match.end()
            line_num = get_line_number_from_position(source, match.start())
            
            # Chercher une vérification SQLCODE dans les 200 caractères suivants
            following = source[fetch_end:fetch_end + 300]
            
            # Ignorer si on trouve un autre EXEC SQL avant la vérification
            next_exec = re.search(r'EXEC\s+SQL', following, re.IGNORECASE)
            next_check = self.SQLCODE_CHECK.search(following)
            
            if next_check is None:
                self.result.issues.append(CursorIssue(
                    cursor_name=cursor_name,
                    issue_type=CursorIssueType.FETCH_WITHOUT_CHECK,
                    line_number=line_num,
                    message=f"FETCH sur '{cursor_name}' sans vérification de SQLCODE/sqlca.sqlcode",
                    severity='info',
                ))
            elif next_exec and next_exec.start() < next_check.start():
                # Il y a un autre EXEC SQL avant la vérification
                self.result.issues.append(CursorIssue(
                    cursor_name=cursor_name,
                    issue_type=CursorIssueType.FETCH_WITHOUT_CHECK,
                    line_number=line_num,
                    message=f"FETCH sur '{cursor_name}': vérification SQLCODE peut-être trop tardive",
                    severity='info',
                ))


def analyze_cursors(source: str) -> CursorAnalysisResult:
    """
    Fonction utilitaire pour analyser les curseurs.
    
    Args:
        source: Code source Pro*C
        
    Returns:
        Résultat de l'analyse
    """
    analyzer = CursorAnalyzer()
    return analyzer.analyze(source)
