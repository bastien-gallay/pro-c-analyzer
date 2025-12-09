"""
Calculateur des métriques Halstead

Les métriques Halstead mesurent la complexité basée sur les opérateurs et opérandes:
- n1 = nombre d'opérateurs distincts
- n2 = nombre d'opérandes distincts
- N1 = nombre total d'opérateurs
- N2 = nombre total d'opérandes

Métriques dérivées:
- Vocabulaire (n) = n1 + n2
- Longueur (N) = N1 + N2
- Volume (V) = N * log2(n)
- Difficulté (D) = (n1/2) * (N2/n2)
- Effort (E) = D * V
- Temps estimé (T) = E / 18 secondes
- Bugs estimés (B) = V / 3000
"""

import math
from dataclasses import dataclass, field
from typing import Optional

from tree_sitter import Node

from .parser import FunctionInfo, ProCParser


@dataclass
class HalsteadMetrics:
    """
    Métriques Halstead pour une fonction.

    Les métriques Halstead mesurent la complexité basée sur les opérateurs
    et opérandes. Formule: Volume = N * log2(n) où N = N1 + N2 et n = n1 + n2.

    Attributes:
        unique_operators: Nombre d'opérateurs distincts (n1)
        unique_operands: Nombre d'opérandes distincts (n2)
        total_operators: Nombre total d'opérateurs (N1)
        total_operands: Nombre total d'opérandes (N2)
        operators: Ensemble des opérateurs trouvés (pour debug)
        operands: Ensemble des opérandes trouvés (pour debug)
    """

    unique_operators: int = 0
    unique_operands: int = 0
    total_operators: int = 0
    total_operands: int = 0
    operators: set[str] = field(default_factory=set)
    operands: set[str] = field(default_factory=set)

    @property
    def vocabulary(self) -> int:
        """n = n1 + n2"""
        return self.unique_operators + self.unique_operands

    @property
    def length(self) -> int:
        """N = N1 + N2"""
        return self.total_operators + self.total_operands

    @property
    def calculated_length(self) -> float:
        """Longueur estimée: N^ = n1*log2(n1) + n2*log2(n2)"""
        if self.unique_operators == 0 or self.unique_operands == 0:
            return 0.0
        return self.unique_operators * math.log2(
            self.unique_operators
        ) + self.unique_operands * math.log2(self.unique_operands)

    @property
    def volume(self) -> float:
        """V = N * log2(n)"""
        if self.vocabulary == 0:
            return 0.0
        return self.length * math.log2(self.vocabulary)

    @property
    def difficulty(self) -> float:
        """D = (n1/2) * (N2/n2)"""
        if self.unique_operands == 0:
            return 0.0
        return (self.unique_operators / 2) * (self.total_operands / self.unique_operands)

    @property
    def effort(self) -> float:
        """E = D * V"""
        return self.difficulty * self.volume

    @property
    def time_seconds(self) -> float:
        """T = E / 18 (temps en secondes selon Halstead)"""
        return self.effort / 18

    @property
    def time_minutes(self) -> float:
        """Temps en minutes"""
        return self.time_seconds / 60

    @property
    def bugs_estimate(self) -> float:
        """B = V / 3000 (estimation du nombre de bugs)"""
        return self.volume / 3000

    def to_dict(self) -> dict:
        return {
            "unique_operators": self.unique_operators,
            "unique_operands": self.unique_operands,
            "total_operators": self.total_operators,
            "total_operands": self.total_operands,
            "vocabulary": self.vocabulary,
            "length": self.length,
            "volume": round(self.volume, 2),
            "difficulty": round(self.difficulty, 2),
            "effort": round(self.effort, 2),
            "time_minutes": round(self.time_minutes, 2),
            "bugs_estimate": round(self.bugs_estimate, 3),
        }


class HalsteadCalculator:
    """
    Calcule les métriques Halstead pour du code C/Pro*C.

    Les métriques Halstead mesurent la complexité basée sur les opérateurs
    et opérandes. Elles permettent d'estimer le volume, la difficulté,
    l'effort et le nombre de bugs potentiels.

    Attributes:
        parser: Parser avec le code source analysé
        _cache: Cache des résultats pour éviter les recalculs
    """

    OPERATORS = {
        # Arithmétiques
        "+",
        "-",
        "*",
        "/",
        "%",
        # Affectation
        "=",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "&=",
        "|=",
        "^=",
        "<<=",
        ">>=",
        # Comparaison
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
        # Logiques
        "&&",
        "||",
        "!",
        # Bits
        "&",
        "|",
        "^",
        "~",
        "<<",
        ">>",
        # Incrémentation
        "++",
        "--",
        # Pointeurs
        "->",
        ".",
        # Ternaire
        "?",
        ":",
        # Virgule
        ",",
        # Sizeof
        "sizeof",
    }

    # Mots-clés considérés comme opérateurs
    KEYWORD_OPERATORS = {
        "if",
        "else",
        "for",
        "while",
        "do",
        "switch",
        "case",
        "default",
        "break",
        "continue",
        "return",
        "goto",
        "struct",
        "union",
        "enum",
        "typedef",
    }

    # Types de nœuds AST qui sont des opérateurs
    OPERATOR_NODE_TYPES = {
        "binary_expression",
        "unary_expression",
        "assignment_expression",
        "update_expression",
        "pointer_expression",
        "field_expression",
        "subscript_expression",
        "call_expression",
        "conditional_expression",
        "sizeof_expression",
        "cast_expression",
    }

    # Types de nœuds AST qui sont des opérandes
    OPERAND_NODE_TYPES = {
        "identifier",
        "number_literal",
        "string_literal",
        "char_literal",
        "true",
        "false",
        "null",
    }

    def __init__(self, parser: ProCParser) -> None:
        """
        Initialise le calculateur de métriques Halstead.

        Args:
            parser: Parser avec le code source analysé
        """
        self.parser = parser
        self._cache: dict[str, HalsteadMetrics] = {}

    def calculate(self, function: FunctionInfo) -> HalsteadMetrics:
        """
        Calcule les métriques Halstead pour une fonction.

        Args:
            function: Information sur la fonction à analyser

        Returns:
            Métriques Halstead
        """
        if function.name in self._cache:
            return self._cache[function.name]

        metrics = HalsteadMetrics()

        if function.node is None:
            self._cache[function.name] = metrics
            return metrics

        operators_count: dict[str, int] = {}
        operands_count: dict[str, int] = {}

        self._collect_metrics(function.node, operators_count, operands_count)

        metrics.operators = set(operators_count.keys())
        metrics.operands = set(operands_count.keys())
        metrics.unique_operators = len(operators_count)
        metrics.unique_operands = len(operands_count)
        metrics.total_operators = sum(operators_count.values())
        metrics.total_operands = sum(operands_count.values())

        self._cache[function.name] = metrics
        return metrics

    def _collect_metrics(
        self, node: Node, operators: dict[str, int], operands: dict[str, int]
    ) -> None:
        """
        Collecte récursivement les opérateurs et opérandes.

        Args:
            node: Nœud AST à analyser
            operators: Dictionnaire pour compter les opérateurs
            operands: Dictionnaire pour compter les opérandes
        """
        node_text = self.parser.get_node_text(node)

        if node.type in self.OPERATOR_NODE_TYPES:
            op = self._extract_operator(node)
            if op:
                operators[op] = operators.get(op, 0) + 1

        if node_text in self.KEYWORD_OPERATORS:
            operators[node_text] = operators.get(node_text, 0) + 1

        if node.type == "identifier":
            parent = node.parent
            if parent and parent.type == "call_expression":
                if node == parent.children[0]:
                    operators[node_text] = operators.get(node_text, 0) + 1
                else:
                    operands[node_text] = operands.get(node_text, 0) + 1
            else:
                operands[node_text] = operands.get(node_text, 0) + 1

        elif node.type == "number_literal":
            operands[node_text] = operands.get(node_text, 0) + 1

        elif node.type == "string_literal":
            operands["<string>"] = operands.get("<string>", 0) + 1

        elif node.type == "char_literal":
            operands[node_text] = operands.get(node_text, 0) + 1

        for child in node.children:
            self._collect_metrics(child, operators, operands)

    def _extract_operator(self, node: Node) -> Optional[str]:
        """
        Extrait l'opérateur d'un nœud d'expression.

        Args:
            node: Nœud AST d'expression

        Returns:
            Opérateur trouvé ou None
        """
        if node.type == "binary_expression":
            for child in node.children:
                text = self.parser.get_node_text(child)
                if text in self.OPERATORS:
                    return text

        elif node.type == "unary_expression":
            for child in node.children:
                text = self.parser.get_node_text(child)
                if text in ("!", "~", "-", "+", "*", "&", "++", "--"):
                    return text

        elif node.type == "assignment_expression":
            for child in node.children:
                text = self.parser.get_node_text(child)
                if "=" in text:
                    return text

        elif node.type == "update_expression":
            return "++" if "++" in self.parser.get_node_text(node) else "--"

        elif node.type == "pointer_expression":
            return "->"

        elif node.type == "field_expression":
            return "." if "." in self.parser.get_node_text(node) else "->"

        elif node.type == "subscript_expression":
            return "[]"

        elif node.type == "call_expression":
            return "()"

        elif node.type == "conditional_expression":
            return "?:"

        elif node.type == "sizeof_expression":
            return "sizeof"

        elif node.type == "cast_expression":
            return "(cast)"

        return None

    def calculate_all(self) -> dict[str, HalsteadMetrics]:
        """
        Calcule les métriques pour toutes les fonctions.

        Returns:
            Dictionnaire {nom_fonction: métriques}
        """
        results = {}
        for func in self.parser.get_functions():
            results[func.name] = self.calculate(func)
        return results


def calculate_halstead(parser: ProCParser, function: FunctionInfo) -> HalsteadMetrics:
    """
    Fonction utilitaire pour calculer les métriques Halstead.

    Args:
        parser: Parser avec le code source
        function: Fonction à analyser

    Returns:
        Métriques Halstead
    """
    calculator = HalsteadCalculator(parser)
    return calculator.calculate(function)
