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
    """
    Informations sur une fonction C.
    
    Attributes:
        name: Nom de la fonction
        start_line: Numéro de ligne de début (1-indexed)
        end_line: Numéro de ligne de fin (1-indexed)
        node: Nœud AST de la fonction (None pour fonctions non-standard)
        parameters: Liste des noms de paramètres
        return_type: Type de retour de la fonction
    """
    name: str
    start_line: int
    end_line: int
    node: Optional[Node]
    parameters: List[str] = field(default_factory=list)
    return_type: str = "void"
    
    @property
    def line_count(self) -> int:
        """Retourne le nombre de lignes de la fonction."""
        return self.end_line - self.start_line + 1


class ProCParser:
    """
    Parser C utilisant tree-sitter.
    
    Extrait les fonctions et leur structure pour analyse.
    Détecte à la fois les fonctions C standard et les fonctions
    avec syntaxe non-standard Pro*C (VOID ...() begin/end).
    
    Attributes:
        _parser: Instance du parser tree-sitter
        _tree: Arbre syntaxique généré
        _source: Code source original
        _source_bytes: Code source encodé en bytes
    """
    
    def __init__(self) -> None:
        """Initialise le parser avec le langage C."""
        self._parser = Parser(Language(tsc.language()))
        self._tree: Optional[Node] = None
        self._source: Optional[str] = None
        self._source_bytes: Optional[bytes] = None
    
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
        """
        Extrait le texte source correspondant à un nœud AST.
        
        Args:
            node: Nœud AST
            
        Returns:
            Texte source du nœud
        """
        if self._source_bytes is None:
            return ""
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
        
        if self._tree:
            self._find_functions(self._tree.root_node, functions)
        
        if self._source:
            alt_functions = self._find_alternative_functions(self._source)
            existing_names = {f.name for f in functions}
            for alt_func in alt_functions:
                if alt_func.name not in existing_names:
                    functions.append(alt_func)
        
        return functions
    
    def _find_functions(self, node: Node, functions: List[FunctionInfo]) -> None:
        """
        Recherche récursivement les définitions de fonctions dans l'AST.
        
        Args:
            node: Nœud AST à parcourir
            functions: Liste à remplir avec les fonctions trouvées
        """
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
        
        declarator = self._find_function_declarator(node)
        
        if declarator:
            name = self._extract_name_from_declarator(declarator)
            parameters = self._extract_parameters_from_declarator(declarator)
        
        return_type = self._extract_return_type(node)
        
        if not name:
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
    
    def _find_function_declarator(self, node: Node) -> Optional[Node]:
        """
        Trouve le declarator de fonction dans un nœud de définition.
        
        Args:
            node: Nœud AST de type 'function_definition'
            
        Returns:
            Nœud declarator si trouvé, None sinon
        """
        for child in node.children:
            if child.type == 'function_declarator':
                return child
            elif child.type == 'pointer_declarator':
                for subchild in child.children:
                    if subchild.type == 'function_declarator':
                        return subchild
        return None
    
    def _extract_name_from_declarator(self, declarator: Node) -> Optional[str]:
        """
        Extrait le nom de fonction depuis un declarator.
        
        Args:
            declarator: Nœud AST de type 'function_declarator'
            
        Returns:
            Nom de la fonction si trouvé, None sinon
        """
        for child in declarator.children:
            if child.type == 'identifier':
                return self.get_node_text(child)
        return None
    
    def _extract_parameters_from_declarator(self, declarator: Node) -> List[str]:
        """
        Extrait les paramètres depuis un declarator.
        
        Args:
            declarator: Nœud AST de type 'function_declarator'
            
        Returns:
            Liste des noms de paramètres
        """
        for child in declarator.children:
            if child.type == 'parameter_list':
                return self._extract_parameters(child)
        return []
    
    def _extract_return_type(self, node: Node) -> str:
        """
        Extrait le type de retour depuis un nœud de définition de fonction.
        
        Args:
            node: Nœud AST de type 'function_definition'
            
        Returns:
            Type de retour (défaut: "void")
        """
        for child in node.children:
            if child.type in ('primitive_type', 'type_identifier', 'sized_type_specifier'):
                return self.get_node_text(child)
        return "void"
    
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
        """
        Extrait les noms des paramètres depuis une liste de paramètres.
        
        Args:
            param_list: Nœud AST de type 'parameter_list'
            
        Returns:
            Liste des noms de paramètres
        """
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
        """
        Retourne le nombre de lignes du source.
        
        Returns:
            Nombre de lignes (0 si pas de source)
        """
        if not self._source:
            return 0
        return self._source.count('\n') + 1
    
    def get_non_empty_line_count(self) -> int:
        """
        Retourne le nombre de lignes non vides.
        
        Returns:
            Nombre de lignes non vides (0 si pas de source)
        """
        if not self._source:
            return 0
        return sum(1 for line in self._source.split('\n') if line.strip())
    
    def _find_alternative_functions(self, source: str) -> List[FunctionInfo]:
        """
        Détecte les fonctions avec syntaxe non-standard Pro*C.
        
        Recherche les patterns comme VOID fonction_name() suivis de 'begin'
        et se terminant par 'end'. Ces fonctions ne sont pas détectées par
        tree-sitter car elles utilisent une syntaxe spécifique à Pro*C.
        
        Args:
            source: Code source à analyser
            
        Returns:
            Liste des fonctions détectées
        """
        functions = []
        lines = source.split('\n')
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
                start_line = i + 1
                
                begin_line = self._find_begin_after_declaration(lines, i)
                
                if begin_line is not None:
                    end_line = self._find_matching_end(lines, begin_line)
                    
                    if end_line is not None:
                        params = self._extract_parameters_from_declaration(line)
                        func_info = self._create_alternative_function_info(
                            func_name, start_line, end_line, return_type, params
                        )
                        functions.append(func_info)
                        i = end_line + 1
                        continue
            
            i += 1
        
        return functions
    
    def _find_begin_after_declaration(self, lines: List[str], start_index: int) -> Optional[int]:
        """
        Trouve le 'begin' correspondant à une déclaration de fonction.
        
        Args:
            lines: Liste des lignes du code source
            start_index: Index de la ligne de déclaration
            
        Returns:
            Index de la ligne contenant 'begin' si trouvé, None sinon
        """
        max_search = min(start_index + 5, len(lines))
        for j in range(start_index, max_search):
            if re.search(r'\bbegin\b', lines[j], re.IGNORECASE):
                return j
        return None
    
    def _find_matching_end(self, lines: List[str], begin_index: int) -> Optional[int]:
        """
        Trouve le 'end' correspondant à un 'begin', en gérant l'imbrication.
        
        Args:
            lines: Liste des lignes du code source
            begin_index: Index de la ligne contenant 'begin'
            
        Returns:
            Index de la ligne contenant le 'end' correspondant si trouvé, None sinon
        """
        depth = 1
        
        for j in range(begin_index + 1, len(lines)):
            line_text = self._remove_comments(lines[j])
            
            begin_count = len(re.findall(r'\bbegin\b', line_text, re.IGNORECASE))
            end_count = len(re.findall(r'\bend\b', line_text, re.IGNORECASE))
            
            depth += begin_count - end_count
            
            if depth == 0:
                return j
        
        return None
    
    def _remove_comments(self, line: str) -> str:
        """
        Retire les commentaires d'une ligne de code.
        
        Args:
            line: Ligne de code
            
        Returns:
            Ligne sans commentaires
        """
        if '//' in line:
            line = line[:line.index('//')]
        line = re.sub(r'/\*.*?\*/', '', line)
        return line
    
    def _extract_parameters_from_declaration(self, declaration_line: str) -> List[str]:
        """
        Extrait les paramètres depuis une déclaration de fonction non-standard.
        
        Args:
            declaration_line: Ligne de déclaration (ex: "VOID func(INT a, STR b)")
            
        Returns:
            Liste des noms de paramètres
        """
        params = []
        param_match = re.search(r'\(([^)]*)\)', declaration_line)
        if param_match:
            param_str = param_match.group(1).strip()
            if param_str:
                param_parts = re.findall(r'([A-Z_][A-Z0-9_]*)\s+(\w+)', param_str, re.IGNORECASE)
                params = [name for _, name in param_parts]
        return params
    
    def _create_alternative_function_info(
        self,
        func_name: str,
        start_line: int,
        end_line: int,
        return_type: str,
        parameters: List[str]
    ) -> FunctionInfo:
        """
        Crée un FunctionInfo pour une fonction avec syntaxe non-standard.
        
        Args:
            func_name: Nom de la fonction
            start_line: Numéro de ligne de début (1-indexed)
            end_line: Index de la ligne contenant 'end' (0-indexed)
            return_type: Type de retour en majuscules
            parameters: Liste des noms de paramètres
            
        Returns:
            FunctionInfo créé
        """
        normalized_return_type = return_type.lower() if return_type != 'VOID' else 'void'
        
        return FunctionInfo(
            name=func_name,
            start_line=start_line,
            end_line=end_line + 1,
            node=None,
            parameters=parameters,
            return_type=normalized_return_type
        )


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
