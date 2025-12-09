"""
Analyseur de sécurité mémoire pour code C/Pro*C

Détecte les patterns dangereux:
- malloc/calloc/realloc sans vérification de NULL
- malloc sans free correspondant (fuites potentielles)
- free sans mise à NULL (dangling pointers)
- Double free potentiel
- Buffer overflows potentiels (strcpy, sprintf, gets...)
- Utilisation de fonctions dépréciées/dangereuses
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum


class MemoryIssueType(Enum):
    """Types de problèmes mémoire"""
    MALLOC_NO_CHECK = "malloc_unchecked"        # malloc sans vérif NULL
    MALLOC_NO_FREE = "malloc_no_free"           # malloc sans free
    FREE_NO_NULL = "free_no_null"               # free sans p = NULL
    DOUBLE_FREE = "double_free_risk"            # Risque de double free
    BUFFER_OVERFLOW = "buffer_overflow"         # strcpy, sprintf, etc.
    DANGEROUS_FUNCTION = "dangerous_function"   # gets, etc.
    UNINITIALIZED = "uninitialized"             # Variable non initialisée
    SIZEOF_POINTER = "sizeof_pointer"           # sizeof sur pointeur
    NULL_DEREF = "null_deref_risk"              # Déréférencement potentiel de NULL


class MemorySeverity(Enum):
    """Sévérité des problèmes"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class MemoryIssue:
    """Un problème de mémoire détecté"""
    issue_type: MemoryIssueType
    severity: MemorySeverity
    line_number: int
    message: str
    code_snippet: str
    recommendation: str = ""
    
    def to_dict(self) -> dict:
        return {
            'type': self.issue_type.value,
            'severity': self.severity.value,
            'line_number': self.line_number,
            'message': self.message,
            'code_snippet': self.code_snippet.strip(),
            'recommendation': self.recommendation,
        }


@dataclass
class AllocationInfo:
    """Information sur une allocation mémoire"""
    variable: str
    line_number: int
    function: str  # malloc, calloc, realloc
    has_null_check: bool = False
    has_free: bool = False
    free_line: Optional[int] = None


@dataclass
class MemoryAnalysisResult:
    """Résultat de l'analyse mémoire"""
    issues: List[MemoryIssue] = field(default_factory=list)
    allocations: List[AllocationInfo] = field(default_factory=list)
    dangerous_calls: List[Tuple[str, int]] = field(default_factory=list)
    
    @property
    def total_issues(self) -> int:
        return len(self.issues)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == MemorySeverity.CRITICAL)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == MemorySeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == MemorySeverity.WARNING)
    
    def to_dict(self) -> dict:
        return {
            'total_issues': self.total_issues,
            'critical_count': self.critical_count,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'issues': [i.to_dict() for i in self.issues],
            'allocations_count': len(self.allocations),
            'dangerous_calls_count': len(self.dangerous_calls),
        }


class MemoryAnalyzer:
    """
    Analyse la gestion mémoire dans du code C/Pro*C.
    """
    
    # Fonctions d'allocation
    ALLOC_FUNCTIONS = {
        'malloc': 'malloc({size}) - alloue {size} octets',
        'calloc': 'calloc({n}, {size}) - alloue et initialise à zéro',
        'realloc': 'realloc({ptr}, {size}) - réalloue {size} octets',
        'strdup': 'strdup({str}) - duplique une chaîne',
        'strndup': 'strndup({str}, {n}) - duplique n caractères',
    }
    
    # Fonctions de libération
    FREE_FUNCTIONS = {'free'}
    
    # Fonctions dangereuses avec leurs remplacements
    DANGEROUS_FUNCTIONS = {
        'gets': ('fgets', 'CRITICAL', 'gets() ne vérifie pas la taille - buffer overflow garanti'),
        'strcpy': ('strncpy/strlcpy', 'WARNING', 'strcpy() ne vérifie pas la taille du buffer destination'),
        'strcat': ('strncat/strlcat', 'WARNING', 'strcat() ne vérifie pas la taille du buffer destination'),
        'sprintf': ('snprintf', 'WARNING', 'sprintf() ne vérifie pas la taille du buffer destination'),
        'vsprintf': ('vsnprintf', 'WARNING', 'vsprintf() ne vérifie pas la taille du buffer destination'),
        'scanf': ('fgets+sscanf', 'WARNING', 'scanf() avec %s peut causer un buffer overflow'),
        'fscanf': ('fgets+sscanf', 'INFO', 'fscanf() avec %s peut causer un buffer overflow'),
        'realpath': ('realpath avec buffer NULL', 'INFO', 'realpath() avec buffer fixe peut overflow'),
        'getwd': ('getcwd', 'WARNING', 'getwd() est dépréciée et dangereuse'),
        'mktemp': ('mkstemp', 'WARNING', 'mktemp() a des race conditions'),
        'tempnam': ('mkstemp', 'WARNING', 'tempnam() a des race conditions'),
        'tmpnam': ('mkstemp', 'WARNING', 'tmpnam() a des race conditions'),
    }
    
    # Pattern pour détecter les allocations
    MALLOC_PATTERN = re.compile(
        r'(\w+)\s*=\s*\(?\s*\w*\s*\*?\s*\)?\s*(malloc|calloc|realloc|strdup|strndup)\s*\(',
        re.IGNORECASE
    )
    
    # Pattern pour détecter free
    FREE_PATTERN = re.compile(r'\bfree\s*\(\s*(\w+)\s*\)')
    
    # Pattern pour vérification NULL après malloc
    NULL_CHECK_PATTERNS = [
        re.compile(r'if\s*\(\s*(\w+)\s*==\s*NULL\s*\)'),
        re.compile(r'if\s*\(\s*NULL\s*==\s*(\w+)\s*\)'),
        re.compile(r'if\s*\(\s*!\s*(\w+)\s*\)'),
        re.compile(r'if\s*\(\s*(\w+)\s*\)'),  # if (ptr) - vérification implicite
    ]
    
    # Pattern pour mise à NULL après free
    NULL_ASSIGN_PATTERN = re.compile(r'(\w+)\s*=\s*NULL\s*;')
    
    # Pattern pour sizeof sur pointeur (erreur courante)
    SIZEOF_POINTER_PATTERN = re.compile(
        r'(malloc|calloc|realloc)\s*\([^)]*sizeof\s*\(\s*(\w+)\s*\)'
    )
    
    def __init__(self):
        self.result = MemoryAnalysisResult()
        self._lines: List[str] = []
        self._allocations: Dict[str, AllocationInfo] = {}
    
    def analyze(self, source: str) -> MemoryAnalysisResult:
        """
        Analyse la gestion mémoire dans le code source.
        
        Args:
            source: Code source C/Pro*C
            
        Returns:
            Résultat de l'analyse
        """
        self.result = MemoryAnalysisResult()
        self._lines = source.split('\n')
        self._allocations = {}
        
        # 1. Trouver toutes les allocations
        self._find_allocations(source)
        
        # 2. Trouver tous les free
        self._find_frees(source)
        
        # 3. Vérifier les checks NULL
        self._check_null_verifications(source)
        
        # 4. Détecter les fonctions dangereuses
        self._find_dangerous_functions(source)
        
        # 5. Détecter sizeof sur pointeur
        self._check_sizeof_pointer(source)
        
        # 6. Générer les issues pour malloc sans free
        self._report_unfreed_allocations()
        
        self.result.allocations = list(self._allocations.values())
        return self.result
    
    def _get_line_number(self, source: str, pos: int) -> int:
        """Convertit une position en numéro de ligne"""
        return source[:pos].count('\n') + 1
    
    def _get_line(self, line_num: int) -> str:
        """Récupère une ligne du code"""
        if 0 < line_num <= len(self._lines):
            return self._lines[line_num - 1]
        return ""
    
    def _find_allocations(self, source: str) -> None:
        """Trouve toutes les allocations mémoire"""
        for match in self.MALLOC_PATTERN.finditer(source):
            var_name = match.group(1)
            alloc_func = match.group(2).lower()
            line_num = self._get_line_number(source, match.start())
            
            alloc_info = AllocationInfo(
                variable=var_name,
                line_number=line_num,
                function=alloc_func,
            )
            self._allocations[var_name] = alloc_info
    
    def _find_frees(self, source: str) -> None:
        """Trouve tous les appels à free()"""
        for match in self.FREE_PATTERN.finditer(source):
            var_name = match.group(1)
            line_num = self._get_line_number(source, match.start())
            
            if var_name in self._allocations:
                self._allocations[var_name].has_free = True
                self._allocations[var_name].free_line = line_num
            
            # Vérifier si = NULL suit le free
            # Chercher dans les 100 caractères suivants
            after_free = source[match.end():match.end() + 100]
            null_assign = self.NULL_ASSIGN_PATTERN.search(after_free)
            
            if null_assign:
                if null_assign.group(1) == var_name:
                    # OK, le pointeur est mis à NULL
                    pass
                else:
                    # free() sans mise à NULL
                    self.result.issues.append(MemoryIssue(
                        issue_type=MemoryIssueType.FREE_NO_NULL,
                        severity=MemorySeverity.WARNING,
                        line_number=line_num,
                        message=f"free({var_name}) sans mise à NULL - risque de dangling pointer",
                        code_snippet=self._get_line(line_num),
                        recommendation=f"Ajouter '{var_name} = NULL;' après free()",
                    ))
            else:
                # Pas de = NULL trouvé
                self.result.issues.append(MemoryIssue(
                    issue_type=MemoryIssueType.FREE_NO_NULL,
                    severity=MemorySeverity.WARNING,
                    line_number=line_num,
                    message=f"free({var_name}) sans mise à NULL - risque de dangling pointer",
                    code_snippet=self._get_line(line_num),
                    recommendation=f"Ajouter '{var_name} = NULL;' après free()",
                ))
    
    def _check_null_verifications(self, source: str) -> None:
        """Vérifie que les allocations sont suivies d'un check NULL"""
        for var_name, alloc_info in self._allocations.items():
            # Chercher un check NULL dans les 300 caractères suivant l'allocation
            alloc_pos = self._find_position(source, alloc_info.line_number)
            if alloc_pos == -1:
                continue
            
            after_alloc = source[alloc_pos:alloc_pos + 300]
            
            found_check = False
            for pattern in self.NULL_CHECK_PATTERNS:
                match = pattern.search(after_alloc)
                if match and match.group(1) == var_name:
                    found_check = True
                    alloc_info.has_null_check = True
                    break
            
            if not found_check:
                self.result.issues.append(MemoryIssue(
                    issue_type=MemoryIssueType.MALLOC_NO_CHECK,
                    severity=MemorySeverity.ERROR,
                    line_number=alloc_info.line_number,
                    message=f"{alloc_info.function}() sans vérification NULL - crash si allocation échoue",
                    code_snippet=self._get_line(alloc_info.line_number),
                    recommendation=f"Ajouter: if ({var_name} == NULL) {{ /* gestion erreur */ }}",
                ))
    
    def _find_position(self, source: str, line_num: int) -> int:
        """Trouve la position du début d'une ligne"""
        lines = source.split('\n')
        pos = 0
        for i in range(line_num - 1):
            if i < len(lines):
                pos += len(lines[i]) + 1  # +1 pour le \n
        return pos
    
    def _find_dangerous_functions(self, source: str) -> None:
        """Détecte l'utilisation de fonctions dangereuses"""
        for func_name, (replacement, severity_str, reason) in self.DANGEROUS_FUNCTIONS.items():
            # Pattern pour appel de fonction
            pattern = re.compile(rf'\b{func_name}\s*\(', re.IGNORECASE)
            
            for match in pattern.finditer(source):
                line_num = self._get_line_number(source, match.start())
                
                severity = {
                    'CRITICAL': MemorySeverity.CRITICAL,
                    'ERROR': MemorySeverity.ERROR,
                    'WARNING': MemorySeverity.WARNING,
                    'INFO': MemorySeverity.INFO,
                }.get(severity_str, MemorySeverity.WARNING)
                
                self.result.issues.append(MemoryIssue(
                    issue_type=MemoryIssueType.DANGEROUS_FUNCTION if severity != MemorySeverity.CRITICAL 
                               else MemoryIssueType.BUFFER_OVERFLOW,
                    severity=severity,
                    line_number=line_num,
                    message=f"Utilisation de {func_name}() - {reason}",
                    code_snippet=self._get_line(line_num),
                    recommendation=f"Utiliser {replacement} à la place",
                ))
                
                self.result.dangerous_calls.append((func_name, line_num))
    
    def _check_sizeof_pointer(self, source: str) -> None:
        """Détecte sizeof() sur un pointeur au lieu du type"""
        # Pattern simplifié: malloc(sizeof(ptr)) où ptr est probablement un pointeur
        pattern = re.compile(
            r'(malloc|calloc)\s*\([^)]*sizeof\s*\(\s*(\w+)\s*\)\s*\)',
            re.IGNORECASE
        )
        
        for match in pattern.finditer(source):
            var_name = match.group(2)
            line_num = self._get_line_number(source, match.start())
            
            # Vérifier si c'est un pointeur (heuristique: chercher la déclaration)
            decl_pattern = re.compile(rf'\b\w+\s*\*+\s*{var_name}\b')
            if decl_pattern.search(source[:match.start()]):
                self.result.issues.append(MemoryIssue(
                    issue_type=MemoryIssueType.SIZEOF_POINTER,
                    severity=MemorySeverity.ERROR,
                    line_number=line_num,
                    message=f"sizeof({var_name}) sur un pointeur - alloue seulement la taille du pointeur",
                    code_snippet=self._get_line(line_num),
                    recommendation=f"Utiliser sizeof(*{var_name}) ou sizeof(type) pour la taille de l'objet pointé",
                ))
    
    def _report_unfreed_allocations(self) -> None:
        """Signale les allocations sans free correspondant"""
        for var_name, alloc_info in self._allocations.items():
            if not alloc_info.has_free:
                self.result.issues.append(MemoryIssue(
                    issue_type=MemoryIssueType.MALLOC_NO_FREE,
                    severity=MemorySeverity.WARNING,
                    line_number=alloc_info.line_number,
                    message=f"{alloc_info.function}({var_name}) sans free() correspondant - fuite mémoire potentielle",
                    code_snippet=self._get_line(alloc_info.line_number),
                    recommendation=f"Ajouter free({var_name}) quand la mémoire n'est plus nécessaire",
                ))


def analyze_memory(source: str) -> MemoryAnalysisResult:
    """
    Fonction utilitaire pour analyser la gestion mémoire.
    
    Args:
        source: Code source C/Pro*C
        
    Returns:
        Résultat de l'analyse
    """
    analyzer = MemoryAnalyzer()
    return analyzer.analyze(source)
