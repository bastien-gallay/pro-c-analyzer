"""
Analyseur de commentaires et inventaire de modules

Détecte:
- TODO, FIXME, HACK, XXX, BUG, NOTE, WARNING dans les commentaires
- Entêtes de fichiers pour l'inventaire des modules
- Documentation des fonctions
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path


@dataclass
class TodoItem:
    """Un élément TODO/FIXME trouvé dans le code"""
    tag: str              # TODO, FIXME, HACK, etc.
    message: str          # Le texte du commentaire
    line_number: int      # Numéro de ligne
    priority: str         # high, medium, low
    context: str          # La ligne de code complète
    
    def to_dict(self) -> dict:
        return {
            'tag': self.tag,
            'message': self.message,
            'line_number': self.line_number,
            'priority': self.priority,
            'context': self.context.strip(),
        }


@dataclass
class ModuleInfo:
    """Informations sur un module (fichier)"""
    filepath: str
    filename: str
    directory: str
    
    # Extrait de l'entête
    title: str = ""
    description: str = ""
    author: str = ""
    date: str = ""
    version: str = ""
    
    # Dépendances détectées
    includes: List[str] = field(default_factory=list)
    exec_sql_includes: List[str] = field(default_factory=list)
    
    # Tags de documentation
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'filepath': self.filepath,
            'filename': self.filename,
            'directory': self.directory,
            'title': self.title,
            'description': self.description,
            'author': self.author,
            'date': self.date,
            'version': self.version,
            'includes': self.includes,
            'exec_sql_includes': self.exec_sql_includes,
            'tags': self.tags,
        }


class CommentAnalyzer:
    """
    Analyse les commentaires du code source.
    """
    
    # Tags à détecter avec leur priorité
    TODO_TAGS = {
        'FIXME': 'high',
        'BUG': 'high',
        'XXX': 'high',
        'HACK': 'medium',
        'TODO': 'medium',
        'NOTE': 'low',
        'WARNING': 'medium',
        'WARN': 'medium',
        'OPTIMIZE': 'low',
        'REVIEW': 'medium',
        'DEPRECATED': 'high',
    }
    
    # Pattern pour les commentaires C
    SINGLE_LINE_COMMENT = re.compile(r'//(.*)$', re.MULTILINE)
    MULTI_LINE_COMMENT = re.compile(r'/\*(.*?)\*/', re.DOTALL)
    
    # Pattern pour les tags TODO/FIXME
    TODO_PATTERN = re.compile(
        r'\b(' + '|'.join(TODO_TAGS.keys()) + r')\b[:\s]*(.*)$',
        re.IGNORECASE | re.MULTILINE
    )
    
    # Patterns pour l'entête de module
    HEADER_PATTERNS = {
        'title': [
            re.compile(r'^\s*\*?\s*(?:Module|File|Fichier|Programme)\s*:\s*(.+)$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^\s*\*?\s*(.+\.pc)\s*[-–]\s*(.+)$', re.MULTILINE),
        ],
        'description': [
            re.compile(r'^\s*\*?\s*(?:Description|Desc|Purpose|But)\s*:\s*(.+)$', re.IGNORECASE | re.MULTILINE),
        ],
        'author': [
            re.compile(r'^\s*\*?\s*(?:Author|Auteur|Created by|Créé par)\s*:\s*(.+)$', re.IGNORECASE | re.MULTILINE),
        ],
        'date': [
            re.compile(r'^\s*\*?\s*(?:Date|Created|Créé le|Modified|Modifié)\s*:\s*(.+)$', re.IGNORECASE | re.MULTILINE),
        ],
        'version': [
            re.compile(r'^\s*\*?\s*(?:Version|Ver|Rev|Revision)\s*:\s*(.+)$', re.IGNORECASE | re.MULTILINE),
        ],
    }
    
    # Pattern pour les #include
    INCLUDE_PATTERN = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
    EXEC_SQL_INCLUDE = re.compile(r'EXEC\s+SQL\s+INCLUDE\s+(\w+)', re.IGNORECASE)
    
    def __init__(self) -> None:
        self.todos: List[TodoItem] = []
        self.module_info: Optional[ModuleInfo] = None
    
    def analyze(self, source: str, filepath: str = "") -> Tuple[List[TodoItem], ModuleInfo]:
        """
        Analyse le code source pour extraire TODO/FIXME et infos module.
        
        Args:
            source: Code source
            filepath: Chemin du fichier
            
        Returns:
            Tuple (liste_todos, info_module)
        """
        self.todos = []
        
        path = Path(filepath) if filepath else Path("unknown.pc")
        self.module_info = ModuleInfo(
            filepath=str(path),
            filename=path.name,
            directory=path.parent.name if path.parent.name else "",
        )
        
        lines = source.split('\n')
        
        # Extraire tous les commentaires
        comments = self._extract_comments(source)
        
        # Chercher les TODO/FIXME
        for comment_text, start_line in comments:
            self._find_todos(comment_text, start_line, lines)
        
        # Analyser l'entête (premier bloc de commentaires)
        self._analyze_header(source)
        
        # Trouver les includes
        self._find_includes(source)
        
        return self.todos, self.module_info
    
    def _extract_comments(self, source: str) -> List[Tuple[str, int]]:
        """Extrait tous les commentaires avec leur numéro de ligne"""
        comments = []
        
        # Commentaires multi-lignes /* */
        for match in self.MULTI_LINE_COMMENT.finditer(source):
            start_pos = match.start()
            line_num = source[:start_pos].count('\n') + 1
            comments.append((match.group(1), line_num))
        
        # Commentaires single-line //
        for match in self.SINGLE_LINE_COMMENT.finditer(source):
            start_pos = match.start()
            line_num = source[:start_pos].count('\n') + 1
            comments.append((match.group(1), line_num))
        
        return comments
    
    def _find_todos(self, comment: str, start_line: int, all_lines: List[str]) -> None:
        """Cherche les tags TODO/FIXME dans un commentaire"""
        for match in self.TODO_PATTERN.finditer(comment):
            tag = match.group(1).upper()
            message = match.group(2).strip()
            
            # Calculer le numéro de ligne exact
            offset = comment[:match.start()].count('\n')
            line_num = start_line + offset
            
            # Récupérer le contexte
            context = ""
            if 0 < line_num <= len(all_lines):
                context = all_lines[line_num - 1]
            
            todo = TodoItem(
                tag=tag,
                message=message,
                line_number=line_num,
                priority=self.TODO_TAGS.get(tag, 'low'),
                context=context,
            )
            self.todos.append(todo)
    
    def _analyze_header(self, source: str) -> None:
        """Analyse l'entête du fichier pour extraire les métadonnées"""
        # Chercher le premier bloc de commentaires
        header_match = self.MULTI_LINE_COMMENT.match(source.lstrip())
        if not header_match:
            # Peut-être des commentaires // au début
            lines = source.split('\n')
            header_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('//'):
                    header_lines.append(stripped[2:].strip())
                elif stripped.startswith('/*'):
                    break
                elif stripped and not stripped.startswith('#'):
                    break
            header_text = '\n'.join(header_lines)
        else:
            header_text = header_match.group(1)
        
        if not header_text:
            return
        
        # Extraire les métadonnées
        for field_name, patterns in self.HEADER_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(header_text)
                if match:
                    value = match.group(1).strip()
                    # Nettoyer les astérisques de début
                    value = re.sub(r'^\*+\s*', '', value)
                    setattr(self.module_info, field_name, value)
                    break
        
        # Si pas de titre, utiliser la première ligne non vide
        if not self.module_info.title:
            for line in header_text.split('\n'):
                clean = re.sub(r'^\s*\*?\s*', '', line).strip()
                if clean and len(clean) > 3:
                    self.module_info.title = clean
                    break
        
        # Extraire la description si pas trouvée
        if not self.module_info.description:
            lines = header_text.split('\n')
            desc_lines = []
            in_desc = False
            for line in lines:
                clean = re.sub(r'^\s*\*?\s*', '', line).strip()
                # Ignorer les lignes de métadonnées
                if ':' in clean and any(k in clean.lower() for k in ['author', 'date', 'version', 'file']):
                    in_desc = False
                    continue
                if clean and not clean.startswith('*'):
                    if self.module_info.title and clean == self.module_info.title:
                        in_desc = True
                        continue
                    if in_desc or not self.module_info.title:
                        desc_lines.append(clean)
            
            if desc_lines:
                self.module_info.description = ' '.join(desc_lines[:3])  # Max 3 lignes
    
    def _find_includes(self, source: str) -> None:
        """Trouve les directives #include et EXEC SQL INCLUDE"""
        # #include standard
        for match in self.INCLUDE_PATTERN.finditer(source):
            include = match.group(1)
            if include not in self.module_info.includes:
                self.module_info.includes.append(include)
        
        # EXEC SQL INCLUDE
        for match in self.EXEC_SQL_INCLUDE.finditer(source):
            include = match.group(1)
            if include not in self.module_info.exec_sql_includes:
                self.module_info.exec_sql_includes.append(include)
    
    def get_todos_by_priority(self) -> Dict[str, List[TodoItem]]:
        """Regroupe les TODOs par priorité"""
        by_priority = {'high': [], 'medium': [], 'low': []}
        for todo in self.todos:
            by_priority[todo.priority].append(todo)
        return by_priority
    
    def get_todos_by_tag(self) -> Dict[str, List[TodoItem]]:
        """Regroupe les TODOs par tag"""
        by_tag: Dict[str, List[TodoItem]] = {}
        for todo in self.todos:
            if todo.tag not in by_tag:
                by_tag[todo.tag] = []
            by_tag[todo.tag].append(todo)
        return by_tag


class ModuleInventory:
    """
    Construit un inventaire des modules d'un projet.
    """
    
    def __init__(self) -> None:
        self.modules: Dict[str, ModuleInfo] = {}
        self.by_directory: Dict[str, List[ModuleInfo]] = {}
    
    def add_module(self, module_info: ModuleInfo) -> None:
        """Ajoute un module à l'inventaire"""
        self.modules[module_info.filepath] = module_info
        
        directory = module_info.directory or "<root>"
        if directory not in self.by_directory:
            self.by_directory[directory] = []
        self.by_directory[directory].append(module_info)
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'inventaire"""
        return {
            'total_modules': len(self.modules),
            'directories': list(self.by_directory.keys()),
            'modules_per_directory': {
                d: len(m) for d, m in self.by_directory.items()
            },
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export complet"""
        return {
            'summary': self.get_summary(),
            'by_directory': {
                d: [m.to_dict() for m in modules]
                for d, modules in self.by_directory.items()
            },
            'modules': {
                path: info.to_dict() 
                for path, info in self.modules.items()
            },
        }


def analyze_comments(source: str, filepath: str = "") -> Tuple[List[TodoItem], ModuleInfo]:
    """
    Fonction utilitaire pour analyser les commentaires.
    
    Args:
        source: Code source
        filepath: Chemin du fichier
        
    Returns:
        Tuple (liste_todos, info_module)
    """
    analyzer = CommentAnalyzer()
    return analyzer.analyze(source, filepath)
