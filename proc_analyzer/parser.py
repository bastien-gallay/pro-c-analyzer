"""
Parser C utilisant tree-sitter
Construit un AST à partir du code C prétraité
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Iterator
import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node


@dataclass
class FunctionInfo:
    """Informations sur une fonction C"""
    name: str
    start_line: int
    end_line: int
    node: Node
    parameters: List[str] = field(default_factory=list)
    return_type: str = "void"
    
    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1


class ProCParser:
    """
    Parser C utilisant tree-sitter.
    Extrait les fonctions et leur structure pour analyse.
    """
    
    def __init__(self) -> None:
        self._parser = Parser(Language(tsc.language()))
        self._tree = None
        self._source = None
        self._source_bytes = None
    
    def parse(self, source: str) -> None:
        """
        Parse le code source C.
        
        Args:
            source: Code C (déjà prétraité, sans EXEC SQL)
        """
        self._source = source
        self._source_bytes = source.encode('utf-8')
        self._tree = self._parser.parse(self._source_bytes)
    
    @property
    def root_node(self) -> Optional[Node]:
        """Retourne le nœud racine de l'AST"""
        return self._tree.root_node if self._tree else None
    
    @property
    def has_errors(self) -> bool:
        """Vérifie si le parsing a généré des erreurs"""
        if not self._tree:
            return True
        return self._has_error_nodes(self._tree.root_node)
    
    def _has_error_nodes(self, node: Node) -> bool:
        """Recherche récursivement des nœuds d'erreur"""
        if node.type == 'ERROR' or node.is_missing:
            return True
        for child in node.children:
            if self._has_error_nodes(child):
                return True
        return False
    
    def get_node_text(self, node: Node) -> str:
        """Extrait le texte source correspondant à un nœud"""
        return self._source_bytes[node.start_byte:node.end_byte].decode('utf-8')
    
    def get_functions(self) -> List[FunctionInfo]:
        """
        Extrait toutes les définitions de fonctions.
        
        Détecte à la fois les fonctions C standard (via tree-sitter)
        et les fonctions avec syntaxe non-standard (VOID ...() avec begin/end).
        
        Returns:
            Liste des fonctions trouvées
        """
        functions = []
        
        # Détecter les fonctions C standard via tree-sitter
        if self._tree:
            self._find_functions(self._tree.root_node, functions)
        
        # Détecter les fonctions avec syntaxe non-standard (VOID ...() begin/end)
        if self._source:
            alt_functions = self._find_alternative_functions(self._source)
            # Éviter les doublons (si une fonction a été détectée par tree-sitter)
            existing_names = {f.name for f in functions}
            for alt_func in alt_functions:
                if alt_func.name not in existing_names:
                    functions.append(alt_func)
        
        return functions
    
    def _find_functions(self, node: Node, functions: List[FunctionInfo]) -> None:
        """Recherche récursivement les définitions de fonctions"""
        if node.type == 'function_definition':
            func_info = self._extract_function_info(node)
            if func_info:
                functions.append(func_info)
        
        for child in node.children:
            self._find_functions(child, functions)
    
    def _extract_function_info(self, node: Node) -> Optional[FunctionInfo]:
        """
        Extrait les informations d'une définition de fonction.
        
        Parse l'AST pour extraire le nom, le type de retour, et les paramètres.
        Gère les cas complexes comme les fonctions retournant des pointeurs.
        
        Args:
            node: Nœud AST de type 'function_definition'
            
        Returns:
            FunctionInfo si l'extraction réussit, None sinon
        """
        name = None
        return_type = "void"
        parameters = []
        
        # Chercher le declarator (contient le nom et les paramètres)
        # L'AST de tree-sitter sépare le type de retour du declarator qui contient
        # le nom et les paramètres, d'où cette recherche en deux étapes
        declarator = None
        for child in node.children:
            if child.type == 'function_declarator':
                declarator = child
                break
            elif child.type == 'pointer_declarator':
                # Fonction retournant un pointeur: le declarator est imbriqué
                # Exemple: int* func() → pointer_declarator contient function_declarator
                for subchild in child.children:
                    if subchild.type == 'function_declarator':
                        declarator = subchild
                        break
            elif child.type in ('primitive_type', 'type_identifier', 'sized_type_specifier'):
                # Le type de retour peut être avant ou dans le declarator selon la syntaxe C
                return_type = self.get_node_text(child)
        
        if declarator:
            # Extraire le nom et les paramètres depuis le declarator
            for child in declarator.children:
                if child.type == 'identifier':
                    name = self.get_node_text(child)
                elif child.type == 'parameter_list':
                    parameters = self._extract_parameters(child)
        
        if not name:
            # Fallback pour les déclarations complexes (fonctions avec qualifiers, etc.)
            # Certaines syntaxes C complexes ne sont pas couvertes par le parsing standard
            name = self._find_function_name(node)
        
        if name:
            return FunctionInfo(
                name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                node=node,
                parameters=parameters,
                return_type=return_type
            )
        
        return None
    
    def _find_function_name(self, node: Node) -> Optional[str]:
        """
        Cherche le nom de fonction dans un nœud de définition.
        
        Méthode de fallback pour les déclarations complexes où le nom
        n'a pas pu être extrait par _extract_function_info.
        
        Args:
            node: Nœud AST à analyser
            
        Returns:
            Nom de la fonction si trouvé, None sinon
        """
        for child in node.children:
            if child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        return self.get_node_text(subchild)
            elif child.type in ('pointer_declarator', 'parenthesized_declarator'):
                result = self._find_function_name(child)
                if result:
                    return result
        return None
    
    def _extract_parameters(self, param_list: Node) -> List[str]:
        """Extrait les noms des paramètres"""
        params = []
        for child in param_list.children:
            if child.type == 'parameter_declaration':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        params.append(self.get_node_text(subchild))
                    elif subchild.type == 'pointer_declarator':
                        for sub2 in subchild.children:
                            if sub2.type == 'identifier':
                                params.append(self.get_node_text(sub2))
        return params
    
    def walk(self, node: Optional[Node] = None) -> Iterator[Node]:
        """
        Générateur pour parcourir l'AST en profondeur.
        
        Args:
            node: Nœud de départ (racine par défaut)
            
        Yields:
            Chaque nœud de l'AST
        """
        if node is None:
            node = self.root_node
        if node is None:
            return
        
        yield node
        for child in node.children:
            yield from self.walk(child)
    
    def find_nodes(self, node_type: str, root: Optional[Node] = None) -> List[Node]:
        """
        Trouve tous les nœuds d'un type donné.
        
        Args:
            node_type: Type de nœud à chercher (ex: 'if_statement')
            root: Nœud racine pour la recherche
            
        Returns:
            Liste des nœuds correspondants
        """
        return [n for n in self.walk(root) if n.type == node_type]
    
    def get_line_count(self) -> int:
        """Retourne le nombre de lignes du source"""
        if not self._source:
            return 0
        return self._source.count('\n') + 1
    
    def get_non_empty_line_count(self) -> int:
        """Retourne le nombre de lignes non vides"""
        if not self._source:
            return 0
        return sum(1 for line in self._source.split('\n') if line.strip())
    
    def _find_alternative_functions(self, source: str) -> List[FunctionInfo]:
        """
        Détecte les fonctions avec syntaxe non-standard.
        
        Recherche les patterns comme:
        - VOID fonction_name()
        - VOID fonction_name( param )
        - INT fonction_name()
        etc. suivis de 'begin' et se terminant par 'end'
        
        Args:
            source: Code source à analyser
            
        Returns:
            Liste des fonctions détectées
        """
        functions = []
        lines = source.split('\n')
        
        # Pattern pour détecter les déclarations de fonctions non-standard
        # Exemples: VOID fonction(), INT fonction(), STR fonction(INT param)
        # On cherche: TYPE nom( ... ) suivi de begin
        func_pattern = re.compile(
            r'^\s*([A-Z_][A-Z0-9_]*)\s+(\w+)\s*\([^)]*\)',
            re.IGNORECASE
        )
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = func_pattern.match(line)
            
            if match:
                return_type = match.group(1).upper()
                func_name = match.group(2)
                start_line = i + 1  # 1-indexed
                
                # Chercher le 'begin' correspondant (peut être sur la même ligne ou suivante)
                begin_line = i
                found_begin = False
                
                # Chercher 'begin' dans les lignes suivantes (max 5 lignes)
                for j in range(i, min(i + 5, len(lines))):
                    if re.search(r'\bbegin\b', lines[j], re.IGNORECASE):
                        begin_line = j
                        found_begin = True
                        break
                
                if found_begin:
                    # Chercher le 'end' correspondant
                    end_line = None
                    depth = 1  # On compte les begin/end imbriqués
                    
                    for j in range(begin_line + 1, len(lines)):
                        line_text = lines[j]
                        # Ignorer les commentaires (// et /* */)
                        # Retirer les commentaires de ligne (//)
                        if '//' in line_text:
                            line_text = line_text[:line_text.index('//')]
                        # Retirer les commentaires de bloc (/* */) - version simple
                        line_text = re.sub(r'/\*.*?\*/', '', line_text)
                        
                        # Compter les begin/end pour gérer l'imbrication
                        begin_count = len(re.findall(r'\bbegin\b', line_text, re.IGNORECASE))
                        end_count = len(re.findall(r'\bend\b', line_text, re.IGNORECASE))
                        
                        depth += begin_count - end_count
                        
                        if depth == 0:
                            end_line = j
                            break
                    
                    if end_line is not None:
                        # Extraire les paramètres de la déclaration
                        params = []
                        param_match = re.search(r'\(([^)]*)\)', line)
                        if param_match:
                            param_str = param_match.group(1).strip()
                            if param_str:
                                # Extraire les noms de paramètres (format: TYPE nom, TYPE nom)
                                param_parts = re.findall(r'([A-Z_][A-Z0-9_]*)\s+(\w+)', param_str, re.IGNORECASE)
                                params = [name for _, name in param_parts]
                        
                        # Créer un FunctionInfo (sans node AST car c'est une fonction non-standard)
                        # On crée un nœud factice pour compatibilité
                        func_info = FunctionInfo(
                            name=func_name,
                            start_line=start_line,
                            end_line=end_line + 1,  # 1-indexed
                            node=None,  # Pas de nœud AST pour ces fonctions
                            parameters=params,
                            return_type=return_type.lower() if return_type != 'VOID' else 'void'
                        )
                        functions.append(func_info)
                        i = end_line + 1
                        continue
            
            i += 1
        
        return functions


def parse_source(source: str) -> ProCParser:
    """
    Fonction utilitaire pour parser du code source.
    
    Args:
        source: Code C à parser
        
    Returns:
        Instance de ProCParser avec l'AST chargé
    """
    parser = ProCParser()
    parser.parse(source)
    return parser
