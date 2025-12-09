"""
Parser C utilisant tree-sitter
Construit un AST à partir du code C prétraité
"""

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
    
    def __init__(self):
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
        
        Returns:
            Liste des fonctions trouvées
        """
        if not self._tree:
            return []
        
        functions = []
        self._find_functions(self._tree.root_node, functions)
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
        """Extrait les informations d'une définition de fonction"""
        name = None
        return_type = "void"
        parameters = []
        
        # Chercher le declarator (contient le nom et les paramètres)
        declarator = None
        for child in node.children:
            if child.type == 'function_declarator':
                declarator = child
                break
            elif child.type == 'pointer_declarator':
                # Fonction retournant un pointeur
                for subchild in child.children:
                    if subchild.type == 'function_declarator':
                        declarator = subchild
                        break
            elif child.type in ('primitive_type', 'type_identifier', 'sized_type_specifier'):
                return_type = self.get_node_text(child)
        
        if declarator:
            # Extraire le nom de la fonction
            for child in declarator.children:
                if child.type == 'identifier':
                    name = self.get_node_text(child)
                elif child.type == 'parameter_list':
                    parameters = self._extract_parameters(child)
        
        if not name:
            # Essayer une autre approche pour les déclarations complexes
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
        """Cherche le nom de fonction dans un nœud de définition"""
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
