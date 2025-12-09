"""
Interface ligne de commande pour l'analyseur Pro*C
"""

import csv
import fnmatch
from pathlib import Path
from typing import Any, Optional

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.table import Table

from .analyzer import AnalysisReport, FileMetrics, ModuleInventory, ProCAnalyzer
from .formatters import HTMLFormatter, JSONFormatter, MarkdownFormatter

console = Console()


def parse_patterns(pattern_str: str) -> list[str]:
    """
    Parse un pattern qui peut contenir plusieurs patterns séparés par des points-virgules.

    Args:
        pattern_str: Pattern(s) glob, séparés par des points-virgules (ex: "*.pc;*.sc;*.inc")

    Returns:
        Liste des patterns individuels
    """
    if not pattern_str:
        return ["*.pc"]

    # Séparer par point-virgule et nettoyer les espaces
    patterns = [p.strip() for p in pattern_str.split(";") if p.strip()]

    # Si aucun pattern valide, retourner le défaut
    return patterns if patterns else ["*.pc"]


def match_case_insensitive(filename: str, pattern: str) -> bool:
    """
    Vérifie si un nom de fichier correspond à un pattern de manière insensible à la casse.

    Args:
        filename: Nom du fichier à tester
        pattern: Pattern glob à utiliser

    Returns:
        True si le fichier correspond au pattern, False sinon
    """
    return fnmatch.fnmatch(filename.casefold(), pattern.casefold())


def find_files_case_insensitive(
    path_obj: Path, patterns: list[str], recursive: bool = True
) -> set[Path]:
    """
    Trouve les fichiers correspondant aux patterns de manière insensible à la casse.

    Args:
        path_obj: Chemin du répertoire de base
        patterns: Liste de patterns glob à utiliser
        recursive: Si True, recherche récursive

    Returns:
        Ensemble de chemins de fichiers correspondant aux patterns
    """
    files_set: set[Path] = set()

    # Lister tous les fichiers du répertoire
    if recursive:
        # Parcourir récursivement tous les fichiers avec rglob
        # rglob('**/*') liste tous les fichiers récursivement
        all_files = [f for f in path_obj.rglob("**/*") if f.is_file()]
    else:
        all_files = [f for f in path_obj.glob("*") if f.is_file()]

    # Filtrer par patterns insensibles à la casse
    for file_path in all_files:
        # Vérifier si le fichier correspond à au moins un pattern
        for pattern in patterns:
            if match_case_insensitive(file_path.name, pattern):
                files_set.add(file_path)
                break

    return files_set


def analyze_with_progress(
    analyzer: ProCAnalyzer,
    path: str,
    pattern: Optional[str] = None,
    ipattern: Optional[str] = None,
    recursive: bool = True,
) -> AnalysisReport:
    """
    Analyse un fichier ou répertoire avec affichage de la progression.

    Args:
        analyzer: Instance de ProCAnalyzer
        path: Chemin du fichier ou répertoire à analyser
        pattern: Pattern(s) glob pour les fichiers, séparés par des points-virgules
                 (ex: "*.pc;*.sc;*.inc") (ignoré si path est un fichier ou si ipattern est fourni)
        ipattern: Pattern(s) glob insensible à la casse pour les fichiers, séparés par des points-virgules
                  (ex: "*.PC;*.SC") (ignoré si path est un fichier, prioritaire sur pattern)
        recursive: Recherche récursive (ignoré si path est un fichier)

    Returns:
        Rapport d'analyse
    """
    path_obj = Path(path)

    if path_obj.is_file():
        # Analyse d'un seul fichier (affichage simple)
        console.print(f"[dim]Analyse du fichier {path_obj.name}...[/dim]")
        metrics = analyzer.analyze_file(path)
        report = AnalysisReport(files=[metrics])
        console.print("[green]✓ Analyse terminée[/green]")
        return report

    # Parser les patterns multiples
    # ipattern est prioritaire sur pattern
    if ipattern is not None:
        patterns = parse_patterns(ipattern)
        use_case_insensitive = True
    elif pattern is not None:
        patterns = parse_patterns(pattern)
        use_case_insensitive = False
    else:
        patterns = ["*.pc"]
        use_case_insensitive = False

    # Analyse d'un répertoire avec barre de progression
    # D'abord, compter les fichiers pour initialiser la barre
    # Collecter tous les fichiers correspondant aux différents patterns
    if use_case_insensitive:
        files_set = find_files_case_insensitive(path_obj, patterns, recursive)
    else:
        found_files: set[Path] = set()
        for pat in patterns:
            if recursive:
                files_list = list(path_obj.rglob(pat))
            else:
                files_list = list(path_obj.glob(pat))
            found_files.update(f for f in files_list if f.is_file())
        files_set = found_files

    # Trier pour avoir un ordre déterministe
    files_list = sorted(files_set)
    total_files = len(files_list)

    if total_files == 0:
        console.print("[yellow]Aucun fichier trouvé.[/yellow]")
        return AnalysisReport()

    console.print(f"[dim]Fichiers trouvés: {total_files}[/dim]")

    # Créer une barre de progression
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Analyse en cours...", total=total_files)

        # Si on utilise la recherche insensible à la casse, analyser directement les fichiers trouvés
        # car analyze_directory utilise rglob qui est sensible à la casse
        if use_case_insensitive:
            # Initialiser l'inventaire des modules si nécessaire
            if analyzer.enable_todos:
                analyzer.module_inventory = ModuleInventory()

            # Analyser directement les fichiers trouvés
            report = AnalysisReport()
            for index, filepath in enumerate(files_list, 1):
                file_name = filepath.name
                progress.update(
                    task, completed=index - 1, description=f"[cyan]Analyse: {file_name}"
                )
                metrics = analyzer.analyze_file(str(filepath))
                report.files.append(metrics)

            if analyzer.enable_todos:
                report.module_inventory = analyzer.module_inventory.to_dict()
        else:
            # Callback pour mettre à jour la progression
            def update_progress(filepath: str, current: int, total: int):
                file_name = Path(filepath).name
                progress.update(task, completed=current, description=f"[cyan]Analyse: {file_name}")

            report = analyzer.analyze_directory(
                path, patterns=patterns, recursive=recursive, progress_callback=update_progress
            )

    console.print(f"[green]✓ Analyse terminée: {len(report.files)} fichier(s) analysé(s)[/green]")
    return report


def severity_color(value: int, low: int, medium: int) -> str:
    """
    Retourne une couleur selon la sévérité d'une valeur.

    Args:
        value: Valeur à évaluer
        low: Seuil bas (vert si <= low)
        medium: Seuil moyen (jaune si <= medium, rouge sinon)

    Returns:
        Nom de couleur Rich (green, yellow, ou red)
    """
    if value <= low:
        return "green"
    elif value <= medium:
        return "yellow"
    else:
        return "red"


def issue_severity_color(severity: str) -> str:
    """
    Retourne la couleur Rich selon la sévérité d'un problème.

    Args:
        severity: Niveau de sévérité (critical, error, warning, info)

    Returns:
        Style de couleur Rich pour l'affichage
    """
    colors = {
        "critical": "red bold",
        "error": "red",
        "warning": "yellow",
        "info": "dim",
    }
    return colors.get(severity, "white")


def print_file_report(metrics: FileMetrics, verbose: bool = False) -> None:
    """
    Affiche le rapport d'analyse pour un fichier.

    Args:
        metrics: Métriques du fichier à afficher
        verbose: Si True, affiche les détails Halstead et autres métriques
    """
    # Titre du fichier
    console.print(f"\n[bold blue]📄 {metrics.filepath}[/bold blue]")

    if metrics.parse_errors and metrics.error_message:
        console.print(f"  [red]⚠ Erreur de parsing: {metrics.error_message}[/red]")
        return
    elif metrics.parse_errors:
        console.print("  [yellow]⚠ Parsing partiel (code non standard détecté)[/yellow]")

    # Module info
    if metrics.module_info:
        title = metrics.module_info.get("title", "")
        desc = metrics.module_info.get("description", "")
        if title:
            console.print(f"  [dim]Module: {title}[/dim]")
        if desc and verbose:
            console.print(
                f"  [dim]{desc[:80]}...[/dim]" if len(desc) > 80 else f"  [dim]{desc}[/dim]"
            )

    # Stats générales
    console.print(f"  Lignes: {metrics.total_lines} (non vides: {metrics.non_empty_lines})")
    console.print(f"  Fonctions: {metrics.function_count}")
    console.print(f"  Blocs SQL: {metrics.total_sql_blocks}")

    if metrics.sql_statistics.get("by_type"):
        sql_types = ", ".join(
            f"{t}: {c}" for t, c in list(metrics.sql_statistics["by_type"].items())[:6]
        )
        console.print(f"  Types SQL: {sql_types}")

    # TODOs
    if metrics.todos:
        high_todos = [t for t in metrics.todos if t.get("priority") == "high"]
        console.print(
            f"  TODO/FIXME: {len(metrics.todos)} ([red]{len(high_todos)} haute priorité[/red])"
        )

    # Problèmes curseurs
    if metrics.cursor_analysis:
        issues = metrics.cursor_analysis.get("total_issues", 0)
        nested = metrics.cursor_analysis.get("nested_cursor_count", 0)
        if issues > 0 or nested > 0:
            console.print(
                f"  Curseurs: {metrics.cursor_analysis.get('total_cursors', 0)} ([yellow]{issues} issues, {nested} imbriqués[/yellow])"
            )

    # Problèmes mémoire
    if metrics.memory_analysis:
        mem_issues = metrics.memory_analysis.get("total_issues", 0)
        critical = metrics.memory_analysis.get("critical_count", 0)
        if mem_issues > 0:
            console.print(f"  Mémoire: [red]{mem_issues} problèmes ({critical} critiques)[/red]")

    if not metrics.functions:
        console.print("  [dim]Aucune fonction trouvée[/dim]")
        return

    # Tableau des fonctions
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Fonction", style="cyan")
    table.add_column("Lignes", justify="right")
    table.add_column("Cyclo", justify="right")
    table.add_column("Cogn", justify="right")
    table.add_column("SQL", justify="right")

    if verbose:
        table.add_column("Halstead Vol", justify="right")
        table.add_column("Bugs Est.", justify="right")

    for func in metrics.functions:
        cyclo_color = severity_color(func.cyclomatic_complexity, 5, 10)
        cognitive_color = severity_color(func.cognitive_complexity, 8, 15)

        row = [
            f"{func.name} (L{func.start_line})",
            str(func.line_count),
            f"[{cyclo_color}]{func.cyclomatic_complexity}[/{cyclo_color}]",
            f"[{cognitive_color}]{func.cognitive_complexity}[/{cognitive_color}]",
            str(func.sql_blocks_count),
        ]

        if verbose and func.halstead:
            row.append(f"{func.halstead.get('volume', 0):.0f}")
            row.append(f"{func.halstead.get('bugs_estimate', 0):.2f}")
        elif verbose:
            row.extend(["", ""])

        table.add_row(*row)

    console.print(table)


def print_todos(report: AnalysisReport) -> None:
    """Affiche les TODOs/FIXME"""
    todos = report.get_all_todos()
    if not todos:
        return

    console.print("\n[bold]📝 TODO/FIXME[/bold]")

    # Grouper par priorité
    by_priority: dict[str, list[tuple[str, dict[str, Any]]]] = {"high": [], "medium": [], "low": []}
    for filepath, todo in todos:
        priority = todo.get("priority", "low")
        by_priority[priority].append((filepath, todo))

    for priority in ["high", "medium", "low"]:
        items = by_priority[priority]
        if not items:
            continue

        color = {"high": "red", "medium": "yellow", "low": "dim"}[priority]
        console.print(f"\n  [{color}]{priority.upper()} ({len(items)})[/{color}]")

        for filepath, todo in items[:10]:  # Limiter à 10 par priorité
            tag = todo.get("tag", "TODO")
            msg = todo.get("message", "")[:60]
            line = todo.get("line_number", 0)
            console.print(f"    [{color}]{tag}[/{color}] {Path(filepath).name}:{line} - {msg}")

        if len(items) > 10:
            console.print(f"    [dim]... et {len(items) - 10} autres[/dim]")


def print_cursor_issues(report: AnalysisReport) -> None:
    """Affiche les problèmes de curseurs"""
    issues = report.get_all_cursor_issues()
    if not issues:
        return

    console.print("\n[bold]🔄 Problèmes de curseurs SQL[/bold]")

    # Trier par sévérité
    for filepath, issue in issues[:15]:
        severity = issue.get("severity", "info")
        color = issue_severity_color(severity)
        cursor = issue.get("cursor_name", "?")
        line = issue.get("line_number", 0)
        msg = issue.get("message", "")

        console.print(f"  [{color}]{severity.upper()}[/{color}] {Path(filepath).name}:{line}")
        console.print(f"    Curseur: {cursor} - {msg}")

    if len(issues) > 15:
        console.print(f"  [dim]... et {len(issues) - 15} autres problèmes[/dim]")


def print_memory_issues(report: AnalysisReport) -> None:
    """Affiche les problèmes mémoire"""
    issues = report.get_all_memory_issues()
    if not issues:
        return

    console.print("\n[bold]🧠 Problèmes de gestion mémoire[/bold]")

    # Grouper par sévérité
    by_severity: dict[str, list[tuple[str, dict[str, Any]]]] = {
        "critical": [],
        "error": [],
        "warning": [],
        "info": [],
    }
    for filepath, issue in issues:
        severity = issue.get("severity", "info")
        by_severity[severity].append((filepath, issue))

    for severity in ["critical", "error", "warning"]:
        items = by_severity[severity]
        if not items:
            continue

        color = issue_severity_color(severity)
        console.print(f"\n  [{color}]{severity.upper()} ({len(items)})[/{color}]")

        for filepath, issue in items[:10]:
            line = issue.get("line_number", 0)
            msg = issue.get("message", "")
            rec = issue.get("recommendation", "")

            console.print(f"    [{color}]►[/{color}] {Path(filepath).name}:{line}")
            console.print(f"      {msg}")
            if rec:
                console.print(f"      [dim]→ {rec}[/dim]")

        if len(items) > 10:
            console.print(f"    [dim]... et {len(items) - 10} autres[/dim]")


def print_module_inventory(report: AnalysisReport) -> None:
    """Affiche l'inventaire des modules"""
    if not report.module_inventory:
        return

    by_dir = report.module_inventory.get("by_directory", {})
    if not by_dir:
        return

    console.print("\n[bold]📦 Inventaire des modules[/bold]")

    for directory, modules in sorted(by_dir.items()):
        console.print(f"\n  [bold cyan]{directory}/[/bold cyan] ({len(modules)} modules)")

        for mod in modules[:5]:
            title = mod.get("title", mod.get("filename", "?"))
            desc = mod.get("description", "")[:50]
            console.print(f"    • {title}")
            if desc:
                console.print(
                    f"      [dim]{desc}...[/dim]" if len(desc) >= 50 else f"      [dim]{desc}[/dim]"
                )

        if len(modules) > 5:
            console.print(f"    [dim]... et {len(modules) - 5} autres modules[/dim]")


def print_summary(report: AnalysisReport, cyclo_threshold: int, cognitive_threshold: int) -> None:
    """Affiche le résumé du rapport"""
    console.print("\n" + "=" * 60)
    console.print("[bold]📊 RÉSUMÉ[/bold]")
    console.print("=" * 60)

    summary_table = Table(box=box.SIMPLE, show_header=False)
    summary_table.add_column("Métrique", style="bold")
    summary_table.add_column("Valeur", justify="right")

    summary_table.add_row("Fichiers analysés", str(report.total_files))
    summary_table.add_row("Fonctions totales", str(report.total_functions))
    summary_table.add_row("Lignes totales", str(report.total_lines))
    summary_table.add_row("Blocs SQL totaux", str(report.total_sql_blocks))
    summary_table.add_row("", "")
    summary_table.add_row("Complexité cyclomatique moyenne", f"{report.avg_cyclomatic:.2f}")
    summary_table.add_row("Complexité cognitive moyenne", f"{report.avg_cognitive:.2f}")
    summary_table.add_row("", "")
    summary_table.add_row("TODO/FIXME", str(report.total_todos))
    summary_table.add_row("Problèmes curseurs", str(report.total_cursor_issues))
    summary_table.add_row("Problèmes mémoire", str(report.total_memory_issues))

    console.print(summary_table)

    # Fonctions à risque
    high_risk = report.get_high_complexity_functions(cyclo_threshold, cognitive_threshold)

    if high_risk:
        console.print(f"\n[bold red]⚠ Fonctions à risque ({len(high_risk)})[/bold red]")
        console.print(f"  (cyclomatic > {cyclo_threshold} ou cognitive > {cognitive_threshold})")

        risk_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        risk_table.add_column("Fichier")
        risk_table.add_column("Fonction")
        risk_table.add_column("Cyclo", justify="right")
        risk_table.add_column("Cogn", justify="right")

        for filepath, func in high_risk[:20]:
            risk_table.add_row(
                Path(filepath).name,
                func.name,
                (
                    f"[red]{func.cyclomatic_complexity}[/red]"
                    if func.cyclomatic_complexity > cyclo_threshold
                    else str(func.cyclomatic_complexity)
                ),
                (
                    f"[red]{func.cognitive_complexity}[/red]"
                    if func.cognitive_complexity > cognitive_threshold
                    else str(func.cognitive_complexity)
                ),
            )

        if len(high_risk) > 20:
            console.print(f"  [dim]... et {len(high_risk) - 20} autres fonctions[/dim]")

        console.print(risk_table)
    else:
        console.print("\n[green]✓ Aucune fonction ne dépasse les seuils de complexité[/green]")


def save_json(report: AnalysisReport, output: str) -> None:
    """Sauvegarde le rapport en JSON"""
    Path(output).write_text(report.to_json(), encoding="utf-8")
    console.print(f"[green]✓ Rapport JSON sauvegardé: {output}[/green]")


def save_csv(report: AnalysisReport, output: str) -> None:
    """Sauvegarde le rapport en CSV"""
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in report.to_csv_rows():
            writer.writerow(row)
    console.print(f"[green]✓ Rapport CSV sauvegardé: {output}[/green]")


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """
    Pro*C Static Analyzer - Analyse de complexité pour code Pro*C

    Calcule la complexité cyclomatique, cognitive, Halstead,
    détecte les TODO/FIXME, curseurs imbriqués et problèmes mémoire.
    """
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--pattern",
    "-p",
    default=None,
    help='Pattern(s) glob pour les fichiers, séparés par des points-virgules (ex: "*.pc;*.sc;*.inc") (défaut: *.pc)',
)
@click.option(
    "--ipattern",
    "-i",
    default=None,
    help='Pattern(s) glob insensible à la casse pour les fichiers, séparés par des points-virgules (ex: "*.PC;*.SC") (prioritaire sur --pattern)',
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "json-pretty", "html", "markdown", "csv"]),
    default="text",
    help="Format de sortie",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Fichier de sortie (requis pour html/markdown, optionnel pour json/csv)",
)
@click.option(
    "--threshold-cyclo", "-tc", default=10, help="Seuil complexité cyclomatique (défaut: 10)"
)
@click.option(
    "--threshold-cognitive", "-tg", default=15, help="Seuil complexité cognitive (défaut: 15)"
)
@click.option(
    "--recursive/--no-recursive", "-r/-R", default=True, help="Recherche récursive (défaut: oui)"
)
@click.option("--verbose", "-v", is_flag=True, help="Mode verbeux (Halstead, détails)")
@click.option("--no-halstead", is_flag=True, help="Désactiver les métriques Halstead")
@click.option("--no-todos", is_flag=True, help="Désactiver la détection TODO/FIXME")
@click.option("--no-cursors", is_flag=True, help="Désactiver l'analyse des curseurs")
@click.option("--no-memory", is_flag=True, help="Désactiver l'analyse mémoire")
def analyze(
    path: str,
    pattern: Optional[str],
    ipattern: Optional[str],
    output_format: str,
    output: Optional[str],
    threshold_cyclo: int,
    threshold_cognitive: int,
    recursive: bool,
    verbose: bool,
    no_halstead: bool,
    no_todos: bool,
    no_cursors: bool,
    no_memory: bool,
):
    """
    Analyse les fichiers Pro*C.

    PATH peut être un fichier ou un répertoire.

    Exemples:

        proc-analyzer analyze program.pc

        proc-analyzer analyze ./src --pattern "*.pc"

        proc-analyzer analyze ./src --pattern "*.pc;*.sc;*.inc"

        proc-analyzer analyze ./src --ipattern "*.PC;*.SC"  # Insensible à la casse

        proc-analyzer analyze ./src -f json -o report.json

        proc-analyzer analyze ./src -v  # Mode verbeux avec Halstead
    """
    analyzer = ProCAnalyzer(
        enable_halstead=not no_halstead,
        enable_todos=not no_todos,
        enable_cursors=not no_cursors,
        enable_memory=not no_memory,
    )
    console.print(
        Panel.fit(
            "[bold]Pro*C Static Analyzer v0.2[/bold]\n"
            "Complexité · TODO/FIXME · Curseurs · Mémoire",
            border_style="blue",
        )
    )

    # Si aucun pattern n'est fourni, utiliser le défaut
    if pattern is None and ipattern is None:
        pattern = "*.pc"

    report = analyze_with_progress(analyzer, path, pattern, ipattern, recursive)

    if not report.files:
        console.print("[yellow]Aucun fichier trouvé.[/yellow]")
        return

    if output_format in ("json", "json-pretty"):
        json_formatter = JSONFormatter(pretty=(output_format == "json-pretty"))
        if output:
            json_formatter.save(report, output)
            console.print(f"[green]✓ Rapport JSON sauvegardé: {output}[/green]")
        else:
            console.print(json_formatter.format(report))

    elif output_format == "html":
        if not output:
            console.print("[red]Erreur: --output est requis pour le format HTML[/red]")
            return
        html_formatter = HTMLFormatter()
        html_formatter.save(report, output)
        console.print(f"[green]✓ Rapport HTML sauvegardé: {output}[/green]")

    elif output_format == "markdown":
        if not output:
            console.print("[red]Erreur: --output est requis pour le format Markdown[/red]")
            return
        markdown_formatter = MarkdownFormatter()
        markdown_formatter.save(report, output)
        console.print(f"[green]✓ Rapport Markdown sauvegardé: {output}[/green]")

    elif output_format == "csv":
        if output:
            save_csv(report, output)
        else:
            for row in report.to_csv_rows():
                console.print(",".join(row))

    else:
        for file_metrics in report.files:
            print_file_report(file_metrics, verbose)

        if verbose:
            print_todos(report)
            print_cursor_issues(report)
            print_memory_issues(report)
            print_module_inventory(report)

        if len(report.files) > 1 or report.total_functions > 0:
            print_summary(report, threshold_cyclo, threshold_cognitive)

        if output:
            json_formatter = JSONFormatter(pretty=True)
            json_formatter.save(report, output)
            console.print(f"[green]✓ Rapport JSON sauvegardé: {output}[/green]")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def todos(path: str):
    """
    Liste tous les TODO/FIXME d'un projet.
    """
    analyzer = ProCAnalyzer(
        enable_halstead=False,
        enable_todos=True,
        enable_cursors=False,
        enable_memory=False,
    )

    report = analyze_with_progress(analyzer, path)

    todos = report.get_all_todos()

    if not todos:
        console.print("[green]✓ Aucun TODO/FIXME trouvé[/green]")
        return

    console.print(f"[bold]📝 {len(todos)} TODO/FIXME trouvés[/bold]\n")

    # Grouper par fichier
    by_file: dict[str, list[dict[str, Any]]] = {}
    for filepath, todo in todos:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append(todo)

    for filepath, file_todos in by_file.items():
        console.print(f"[bold blue]{Path(filepath).name}[/bold blue]")
        for todo in file_todos:
            tag = todo.get("tag", "TODO")
            priority = todo.get("priority", "low")
            msg = todo.get("message", "")
            line = todo.get("line_number", 0)

            color = {"high": "red", "medium": "yellow", "low": "dim"}[priority]
            console.print(f"  [{color}]{tag}[/{color}] L{line}: {msg}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def security(path: str):
    """
    Analyse de sécurité: mémoire et curseurs dangereux.
    """
    analyzer = ProCAnalyzer(
        enable_halstead=False,
        enable_todos=False,
        enable_cursors=True,
        enable_memory=True,
    )

    report = analyze_with_progress(analyzer, path)

    console.print(Panel.fit("[bold]🔒 Analyse de sécurité Pro*C[/bold]", border_style="red"))

    # Problèmes mémoire
    print_memory_issues(report)

    # Problèmes curseurs
    print_cursor_issues(report)

    # Résumé
    total_issues = report.total_memory_issues + report.total_cursor_issues

    if total_issues == 0:
        console.print("\n[green]✓ Aucun problème de sécurité détecté[/green]")
    else:
        console.print(f"\n[bold red]⚠ {total_issues} problèmes de sécurité détectés[/bold red]")
        console.print(f"  - Mémoire: {report.total_memory_issues}")
        console.print(f"  - Curseurs: {report.total_cursor_issues}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def inventory(path: str):
    """
    Affiche l'inventaire des modules du projet.
    """
    analyzer = ProCAnalyzer(
        enable_halstead=False,
        enable_todos=True,
        enable_cursors=False,
        enable_memory=False,
    )

    path_obj = Path(path)

    if path_obj.is_file():
        console.print("[yellow]Utilisez un répertoire pour l'inventaire[/yellow]")
        return

    report = analyze_with_progress(analyzer, path)

    console.print(Panel.fit(f"[bold]📦 Inventaire du projet[/bold]\n{path}", border_style="blue"))

    if not report.module_inventory:
        console.print("[yellow]Aucun module trouvé[/yellow]")
        return

    by_dir = report.module_inventory.get("by_directory", {})

    for directory, modules in sorted(by_dir.items()):
        console.print(f"\n[bold cyan]📁 {directory}/[/bold cyan]")

        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Fichier")
        table.add_column("Titre/Description")
        table.add_column("Includes")

        for mod in modules:
            filename = mod.get("filename", "?")
            title = mod.get("title", "")
            desc = mod.get("description", "")[:40]
            includes = len(mod.get("includes", [])) + len(mod.get("exec_sql_includes", []))

            display = title or desc or filename
            if len(display) > 50:
                display = display[:47] + "..."

            table.add_row(filename, display, str(includes))

        console.print(table)

    # Stats
    summary = report.module_inventory.get("summary", {})
    console.print(
        f"\n[bold]Total: {summary.get('total_modules', 0)} modules dans {len(by_dir)} répertoires[/bold]"
    )


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def preprocess(path: str):
    """
    Affiche le code prétraité (sans les blocs EXEC SQL).

    Utile pour debugger le parsing.
    """
    from .preprocessor import preprocess_file

    processed, blocks = preprocess_file(path)

    console.print(f"[bold]Blocs EXEC SQL trouvés: {len(blocks)}[/bold]")
    for block in blocks[:20]:
        console.print(f"  L{block.line_number}: {block.sql_type}")

    if len(blocks) > 20:
        console.print(f"  ... et {len(blocks) - 20} autres")

    console.print("\n[bold]Code prétraité:[/bold]")
    console.print(processed)


def main() -> None:
    """
    Point d'entrée principal de l'application CLI.

    Démarre l'interface en ligne de commande avec Click.
    """
    cli()


if __name__ == "__main__":
    main()
