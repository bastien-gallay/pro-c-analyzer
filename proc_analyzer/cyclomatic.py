"""
Calculateur de complexité cyclomatique (McCabe)
M = E - N + 2P où:
- E = nombre d'arêtes dans le graphe de flot de contrôle
- N = nombre de nœuds
- P = nombre de composants connexes (généralement 1 pour une fonction)

En pratique, on compte: 1 + nombre de points de décision
"""

from typing import Any

from tree_sitter import Node

from .parser import FunctionInfo, ProCParser


class CyclomaticCalculator:
    """
    Calcule la complexité cyclomatique selon McCabe.

    La complexité cyclomatique mesure le nombre de chemins linéairement
    indépendants à travers le code source. Formule: M = E - N + 2P où
    E = nombre d'arêtes, N = nombre de nœuds, P = composants connexes.
    En pratique, on compte: 1 + nombre de points de décision.

    Attributes:
        parser: Parser avec le code source analysé
        _cache: Cache des résultats pour éviter les recalculs
    """

    BRANCHING_NODES = {
        "if_statement",
        "while_statement",
        "for_statement",
        "do_statement",
        "case_statement",
        "conditional_expression",
        "catch_clause",
    }

    LOGICAL_OPERATORS = {"&&", "||"}

    def __init__(self, parser: ProCParser) -> None:
        """
        Initialise le calculateur de complexité cyclomatique.

        Args:
            parser: Parser avec le code source analysé
        """
        self.parser = parser
        self._cache: dict[str, int] = {}

    def calculate(self, function: FunctionInfo) -> int:
        """
        Calcule la complexité cyclomatique d'une fonction.

        Args:
            function: Information sur la fonction à analyser

        Returns:
            Complexité cyclomatique (minimum 1)
        """
        if function.name in self._cache:
            return self._cache[function.name]

        complexity = 1

        if function.node is None:
            self._cache[function.name] = complexity
            return complexity

        for node in self.parser.walk(function.node):
            if node.type in self.BRANCHING_NODES:
                complexity += 1

            if node.type == "binary_expression":
                operator = self._get_operator(node)
                if operator in self.LOGICAL_OPERATORS:
                    complexity += 1

        self._cache[function.name] = complexity
        return complexity

    def _get_operator(self, binary_expr: Node) -> str:
        """
        Extrait l'opérateur d'une expression binaire.

        Args:
            binary_expr: Nœud AST de type 'binary_expression'

        Returns:
            Opérateur trouvé ('&&', '||') ou chaîne vide
        """
        for child in binary_expr.children:
            if child.type in ("&&", "||", "and", "or"):
                return self.parser.get_node_text(child)
            if child.is_named and child.type == "binary_expression":
                continue
            text = self.parser.get_node_text(child)
            if text in self.LOGICAL_OPERATORS:
                return text
        return ""

    def calculate_all(self) -> dict[str, int]:
        """
        Calcule la complexité pour toutes les fonctions.

        Returns:
            Dictionnaire {nom_fonction: complexité}
        """
        results = {}
        for func in self.parser.get_functions():
            results[func.name] = self.calculate(func)
        return results

    def get_details(self, function: FunctionInfo) -> dict[str, Any]:
        """
        Retourne le détail des contributeurs à la complexité.

        Args:
            function: Fonction à analyser

        Returns:
            Dictionnaire avec le détail par type de structure
        """
        details = {
            "if_count": 0,
            "loop_count": 0,
            "case_count": 0,
            "ternary_count": 0,
            "logical_and_count": 0,
            "logical_or_count": 0,
        }

        if function.node is None:
            details["total"] = self.calculate(function)
            return details

        for node in self.parser.walk(function.node):
            if node.type == "if_statement":
                details["if_count"] += 1
            elif node.type in ("while_statement", "for_statement", "do_statement"):
                details["loop_count"] += 1
            elif node.type == "case_statement":
                details["case_count"] += 1
            elif node.type == "conditional_expression":
                details["ternary_count"] += 1
            elif node.type == "binary_expression":
                operator = self._get_operator(node)
                if operator == "&&":
                    details["logical_and_count"] += 1
                elif operator == "||":
                    details["logical_or_count"] += 1

        details["total"] = self.calculate(function)
        return details


def calculate_cyclomatic(parser: ProCParser, function: FunctionInfo) -> int:
    """
    Fonction utilitaire pour calculer la complexité cyclomatique.

    Args:
        parser: Parser avec le code source
        function: Fonction à analyser

    Returns:
        Complexité cyclomatique
    """
    calculator = CyclomaticCalculator(parser)
    return calculator.calculate(function)
