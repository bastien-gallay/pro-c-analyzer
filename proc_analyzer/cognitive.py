"""
Calculateur de complexité cognitive (inspiré SonarSource)

La complexité cognitive mesure la difficulté à comprendre le code,
contrairement à la complexité cyclomatique qui mesure la difficulté à tester.

Règles principales:
1. +1 pour chaque structure de contrôle (if, for, while, switch, etc.)
2. +1 supplémentaire par niveau d'imbrication pour les structures imbriquées
3. +1 pour les breaks/continues vers des labels
4. +1 pour chaque opérateur logique dans une séquence mixte
5. Pas d'incrémentation pour else, elif (contrairement à cyclomatic)
"""

from tree_sitter import Node
from typing import Dict, List, Tuple, Any
from .parser import FunctionInfo, ProCParser


class CognitiveCalculator:
    """
    Calcule la complexité cognitive selon les principes SonarSource.
    
    Cette métrique évalue l'effort mental nécessaire pour comprendre le code,
    en pénalisant particulièrement les structures imbriquées.
    """
    
    # Structures qui incrémentent la complexité ET augmentent l'imbrication
    # Ces structures créent un nouveau niveau d'imbrication qui pénalise
    # la lisibilité selon les principes SonarSource (complexité cognitive)
    NESTING_STRUCTURES = {
        'if_statement',
        'while_statement', 
        'for_statement',
        'do_statement',
        'switch_statement',
        'conditional_expression',  # ternaire
    }
    
    # Structures qui incrémentent la complexité SANS augmenter l'imbrication
    # Contrairement aux structures ci-dessus, celles-ci ajoutent de la complexité
    # mais ne créent pas un nouveau niveau d'imbrication (donc pas de pénalité supplémentaire)
    NON_NESTING_INCREMENTS = {
        'else_clause',      # else ajoute 1 mais garde le même niveau d'imbrication
        'case_statement',   # case dans switch - même niveau que le switch
        'goto_statement',   # goto - saut mais pas d'imbrication
    }
    
    # Les breaks/continues vers des labels ajoutent +1 car ils créent
    # un flux de contrôle non linéaire difficile à suivre mentalement
    JUMP_STATEMENTS = {'break_statement', 'continue_statement'}
    
    def __init__(self, parser: ProCParser) -> None:
        self.parser = parser
        self._cache: Dict[str, int] = {}
    
    def calculate(self, function: FunctionInfo) -> int:
        """
        Calcule la complexité cognitive d'une fonction.
        
        Args:
            function: Information sur la fonction à analyser
            
        Returns:
            Complexité cognitive
        """
        if function.name in self._cache:
            return self._cache[function.name]
        
        complexity = 0
        
        # Trouver le corps de la fonction (compound_statement)
        body = self._find_function_body(function.node)
        if body:
            complexity = self._calculate_recursive(body, nesting_level=0)
        
        self._cache[function.name] = complexity
        return complexity
    
    def _find_function_body(self, func_node: Node) -> Node:
        """Trouve le compound_statement (corps) de la fonction"""
        for child in func_node.children:
            if child.type == 'compound_statement':
                return child
        return None
    
    def _calculate_recursive(self, node: Node, nesting_level: int) -> int:
        """
        Calcule récursivement la complexité cognitive.
        
        Args:
            node: Nœud courant
            nesting_level: Niveau d'imbrication actuel
            
        Returns:
            Complexité pour ce sous-arbre
        """
        if node.type in self.NESTING_STRUCTURES:
            return self._calculate_nesting_structure(node, nesting_level)
        elif node.type == 'case_statement':
            return self._calculate_case_statement(node, nesting_level)
        elif node.type == 'goto_statement':
            return 1
        elif node.type in self.JUMP_STATEMENTS:
            return 1 if self._has_label(node) else 0
        elif node.type == 'binary_expression':
            return self._count_logical_sequences(node)
        else:
            return self._calculate_default(node, nesting_level)
    
    def _calculate_nesting_structure(self, node: Node, nesting_level: int) -> int:
        """
        Calcule la complexité pour une structure qui incrémente ET augmente l'imbrication.
        
        Args:
            node: Nœud de structure (if, while, for, etc.)
            nesting_level: Niveau d'imbrication actuel
            
        Returns:
            Complexité pour cette structure et ses enfants
        """
        # +1 pour la structure + niveau d'imbrication actuel
        complexity = 1 + nesting_level
        
        for child in node.children:
            if child.type == 'compound_statement':
                complexity += self._calculate_recursive(child, nesting_level + 1)
            elif child.type == 'else_clause':
                complexity += self._calculate_else_clause(child, nesting_level)
            elif child.type == 'if_statement':
                # else if chaîné - ne pas augmenter l'imbrication
                complexity += self._calculate_recursive(child, nesting_level)
            else:
                complexity += self._calculate_recursive(child, nesting_level)
        
        return complexity
    
    def _calculate_else_clause(self, else_node: Node, nesting_level: int) -> int:
        """
        Calcule la complexité pour une clause else.
        
        else: +1 mais garde le même niveau pour son contenu (sauf else if).
        
        Args:
            else_node: Nœud else_clause
            nesting_level: Niveau d'imbrication actuel
            
        Returns:
            Complexité pour la clause else
        """
        complexity = 1
        
        for subchild in else_node.children:
            if subchild.type == 'compound_statement':
                complexity += self._calculate_recursive(subchild, nesting_level + 1)
            elif subchild.type == 'if_statement':
                # else if: le if sera compté normalement sans augmenter l'imbrication
                complexity += self._calculate_recursive(subchild, nesting_level)
            else:
                complexity += self._calculate_recursive(subchild, nesting_level + 1)
        
        return complexity
    
    def _calculate_case_statement(self, node: Node, nesting_level: int) -> int:
        """
        Calcule la complexité pour un case statement.
        
        case incrémente +1 mais n'augmente pas l'imbrication.
        
        Args:
            node: Nœud case_statement
            nesting_level: Niveau d'imbrication actuel
            
        Returns:
            Complexité pour le case et ses enfants
        """
        complexity = 1
        for child in node.children:
            complexity += self._calculate_recursive(child, nesting_level)
        return complexity
    
    def _calculate_default(self, node: Node, nesting_level: int) -> int:
        """
        Calcule la complexité pour un nœud par défaut (récursion simple).
        
        Args:
            node: Nœud à traiter
            nesting_level: Niveau d'imbrication actuel
            
        Returns:
            Complexité pour ce nœud et ses enfants
        """
        complexity = 0
        for child in node.children:
            complexity += self._calculate_recursive(child, nesting_level)
        return complexity
    
    def _has_label(self, jump_node: Node) -> bool:
        """Vérifie si un break/continue a un label"""
        for child in jump_node.children:
            if child.type == 'statement_identifier' or child.type == 'identifier':
                return True
        return False
    
    def _count_logical_sequences(self, node: Node) -> int:
        """
        Compte les séquences d'opérateurs logiques.
        
        Chaque changement d'opérateur dans une chaîne ajoute +1 à la complexité.
        Cela reflète l'effort mental supplémentaire pour comprendre des conditions
        avec des opérateurs mixtes.
        
        Args:
            node: Nœud AST de type 'binary_expression'
            
        Returns:
            Nombre de séquences logiques (changements d'opérateur + 1)
            
        Examples:
            a && b && c → 1 séquence (tous &&)
            a && b || c → 2 séquences (changement && → ||)
        """
        operators = self._collect_logical_operators(node)
        
        if not operators:
            return 0
        
        # Compter les séquences (changements d'opérateur + 1)
        sequences = 1
        for i in range(1, len(operators)):
            if operators[i] != operators[i-1]:
                sequences += 1
        
        return sequences
    
    def _collect_logical_operators(self, node: Node) -> List[str]:
        """
        Collecte tous les opérateurs logiques d'une expression binaire.
        
        Parcourt récursivement l'arbre d'expression pour extraire tous
        les opérateurs && et ||. Utilisé pour calculer les séquences logiques
        qui augmentent la complexité cognitive.
        
        Args:
            node: Nœud AST de type 'binary_expression'
            
        Returns:
            Liste des opérateurs logiques trouvés (&&, ||)
        """
        operators = []
        
        if node.type != 'binary_expression':
            return operators
        
        # Trouver l'opérateur
        op = None
        left = None
        right = None
        
        for child in node.children:
            text = self.parser.get_node_text(child)
            if text in ('&&', '||'):
                op = text
            elif child.type == 'binary_expression' and not left:
                left = child
            elif child.type == 'binary_expression':
                right = child
        
        # Récursion à gauche
        if left:
            operators.extend(self._collect_logical_operators(left))
        
        # Ajouter l'opérateur courant
        if op:
            operators.append(op)
        
        # Récursion à droite
        if right:
            operators.extend(self._collect_logical_operators(right))
        
        return operators
    
    def calculate_all(self) -> Dict[str, int]:
        """
        Calcule la complexité pour toutes les fonctions.
        
        Returns:
            Dictionnaire {nom_fonction: complexité}
        """
        results = {}
        for func in self.parser.get_functions():
            results[func.name] = self.calculate(func)
        return results
    
    def get_details(self, function: FunctionInfo) -> Dict[str, Any]:
        """
        Retourne le détail des contributeurs à la complexité.
        
        Args:
            function: Fonction à analyser
            
        Returns:
            Dictionnaire avec le détail par type de structure et imbrication
        """
        details = {
            'if_count': 0,
            'loop_count': 0,
            'switch_count': 0,
            'case_count': 0,
            'ternary_count': 0,
            'else_count': 0,
            'goto_count': 0,
            'labeled_jump_count': 0,
            'logical_sequences': 0,
            'max_nesting': 0,
            'nesting_penalty': 0,
        }
        
        body = self._find_function_body(function.node)
        if body:
            self._collect_details(body, 0, details)
        
        details['total'] = self.calculate(function)
        return details
    
    def _collect_details(self, node: Node, nesting: int, details: Dict[str, Any]) -> None:
        """Collecte les détails récursivement"""
        details['max_nesting'] = max(details['max_nesting'], nesting)
        
        if node.type == 'if_statement':
            details['if_count'] += 1
            details['nesting_penalty'] += nesting
            new_nesting = nesting + 1
        elif node.type in ('while_statement', 'for_statement', 'do_statement'):
            details['loop_count'] += 1
            details['nesting_penalty'] += nesting
            new_nesting = nesting + 1
        elif node.type == 'switch_statement':
            details['switch_count'] += 1
            details['nesting_penalty'] += nesting
            new_nesting = nesting + 1
        elif node.type == 'conditional_expression':
            details['ternary_count'] += 1
            details['nesting_penalty'] += nesting
            new_nesting = nesting + 1
        elif node.type == 'case_statement':
            details['case_count'] += 1
            new_nesting = nesting
        elif node.type == 'else_clause':
            details['else_count'] += 1
            new_nesting = nesting
        elif node.type == 'goto_statement':
            details['goto_count'] += 1
            new_nesting = nesting
        elif node.type in self.JUMP_STATEMENTS and self._has_label(node):
            details['labeled_jump_count'] += 1
            new_nesting = nesting
        elif node.type == 'binary_expression':
            details['logical_sequences'] += self._count_logical_sequences(node)
            return  # Ne pas descendre
        else:
            new_nesting = nesting
        
        for child in node.children:
            self._collect_details(child, new_nesting, details)


def calculate_cognitive(parser: ProCParser, function: FunctionInfo) -> int:
    """
    Fonction utilitaire pour calculer la complexité cognitive.
    
    Args:
        parser: Parser avec le code source
        function: Fonction à analyser
        
    Returns:
        Complexité cognitive
    """
    calculator = CognitiveCalculator(parser)
    return calculator.calculate(function)
