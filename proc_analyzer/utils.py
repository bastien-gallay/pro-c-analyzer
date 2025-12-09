"""
Utilitaires partagés pour l'analyseur Pro*C.

Ce module contient des fonctions utilitaires réutilisables
pour éviter la duplication de code (principe DRY).
"""


def get_line_number_from_position(source: str, position: int) -> int:
    """
    Convertit une position dans le code source en numéro de ligne.

    Args:
        source: Code source complet
        position: Position dans le source (index de caractère, 0-indexed)

    Returns:
        Numéro de ligne (1-indexed)

    Examples:
        >>> source = "line1\\nline2\\nline3"
        >>> get_line_number_from_position(source, 0)
        1
        >>> get_line_number_from_position(source, 7)
        2
    """
    return source[:position].count("\n") + 1
