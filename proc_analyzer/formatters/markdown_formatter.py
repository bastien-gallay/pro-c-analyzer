"""
Formatter Markdown pour les rapports d'analyse.
"""

from datetime import datetime
from pathlib import Path

from ..analyzer import AnalysisReport, FileMetrics


class MarkdownFormatter:
    """
    Formatter pour générer des rapports au format Markdown.
    
    Génère du Markdown compatible GitHub/GitLab avec tableaux,
    badges et structure claire.
    """
    
    def format(self, report: AnalysisReport) -> str:
        """
        Formate un rapport en Markdown.
        
        Args:
            report: Rapport d'analyse à formater
            
        Returns:
            Chaîne Markdown formatée
        """
        parts = [
            self._markdown_header(),
            self._markdown_summary(report),
            self._markdown_files(report),
            self._markdown_todos(report),
            self._markdown_cursor_issues(report),
            self._markdown_memory_issues(report),
        ]
        return '\n\n'.join(parts)
    
    def save(self, report: AnalysisReport, output_path: str) -> None:
        """
        Sauvegarde un rapport Markdown dans un fichier.
        
        Args:
            report: Rapport d'analyse à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        output = Path(output_path)
        output.write_text(self.format(report), encoding='utf-8')
    
    def _markdown_header(self) -> str:
        """Génère l'en-tête Markdown."""
        return f"""# Pro*C Static Analyzer - Rapport d'analyse

**Généré le** {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"""
    
    def _markdown_summary(self, report: AnalysisReport) -> str:
        """Génère la section résumé."""
        return f"""## 📊 Résumé

| Métrique | Valeur |
|----------|--------|
| Fichiers analysés | {report.total_files} |
| Fonctions totales | {report.total_functions} |
| Lignes de code | {report.total_lines:,} |
| Blocs SQL totaux | {report.total_sql_blocks} |
| Complexité cyclomatique moyenne | {report.avg_cyclomatic:.2f} |
| Complexité cognitive moyenne | {report.avg_cognitive:.2f} |
| TODO/FIXME | {report.total_todos} |
| Problèmes curseurs | {report.total_cursor_issues} |
| Problèmes mémoire | {report.total_memory_issues} |"""
    
    def _markdown_files(self, report: AnalysisReport) -> str:
        """Génère la section des fichiers."""
        if not report.files:
            return ""
        
        parts = ['## 📄 Fichiers analysés']
        
        for file_metrics in report.files:
            parts.append(self._markdown_file_section(file_metrics))
        
        return '\n\n'.join(parts)
    
    def _markdown_file_section(self, metrics: FileMetrics) -> str:
        """Génère la section Markdown pour un fichier."""
        file_name = Path(metrics.filepath).name
        parts = [f'### {file_name}']
        
        # Stats générales
        parts.append(f"**Lignes:** {metrics.total_lines} (non vides: {metrics.non_empty_lines})  ")
        parts.append(f"**Fonctions:** {metrics.function_count}  ")
        parts.append(f"**Blocs SQL:** {metrics.total_sql_blocks}")
        
        if metrics.todos:
            high_todos = sum(1 for t in metrics.todos if t.get('priority') == 'high')
            parts.append(f"  ")
            parts.append(f"**TODO/FIXME:** {len(metrics.todos)} ({high_todos} haute priorité)")
        
        if metrics.cursor_analysis:
            issues = metrics.cursor_analysis.get('total_issues', 0)
            nested = metrics.cursor_analysis.get('nested_cursor_count', 0)
            if issues > 0 or nested > 0:
                parts.append(f"  ")
                parts.append(f"**Curseurs:** {metrics.cursor_analysis.get('total_cursors', 0)} ({issues} issues, {nested} imbriqués)")
        
        if metrics.memory_analysis:
            mem_issues = metrics.memory_analysis.get('total_issues', 0)
            critical = metrics.memory_analysis.get('critical_count', 0)
            if mem_issues > 0:
                parts.append(f"  ")
                parts.append(f"**Mémoire:** {mem_issues} problèmes ({critical} critiques)")
        
        # Tableau des fonctions
        if metrics.functions:
            parts.append('\n#### Fonctions\n')
            parts.append('| Fonction | Lignes | Cyclo | Cogn | SQL |')
            parts.append('|----------|--------|-------|------|-----|')
            
            for func in metrics.functions:
                cyclo_badge = self._complexity_badge(func.cyclomatic_complexity, 5, 10)
                cogn_badge = self._complexity_badge(func.cognitive_complexity, 8, 15)
                
                func_name = func.name.replace('|', '\\|')
                parts.append(
                    f"| `{func_name}` (L{func.start_line}) | "
                    f"{func.line_count} | {cyclo_badge} {func.cyclomatic_complexity} | "
                    f"{cogn_badge} {func.cognitive_complexity} | {func.sql_blocks_count} |"
                )
        
        return '\n'.join(parts)
    
    def _markdown_todos(self, report: AnalysisReport) -> str:
        """Génère la section TODOs."""
        todos = report.get_all_todos()
        if not todos:
            return ""
        
        parts = ['## 📝 TODO/FIXME']
        
        # Grouper par priorité
        by_priority = {'high': [], 'medium': [], 'low': []}
        for filepath, todo in todos:
            priority = todo.get('priority', 'low')
            by_priority[priority].append((filepath, todo))
        
        for priority in ['high', 'medium', 'low']:
            items = by_priority[priority]
            if not items:
                continue
            
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '⚪'}[priority]
            parts.append(f'\n### {emoji} {priority.upper()} ({len(items)})')
            
            for filepath, todo in items[:20]:  # Limiter à 20 par priorité
                tag = todo.get('tag', 'TODO')
                msg = todo.get('message', '').replace('|', '\\|')
                line = todo.get('line_number', 0)
                file_name = Path(filepath).name
                
                parts.append(f"- **{tag}** `{file_name}:{line}` - {msg}")
            
            if len(items) > 20:
                parts.append(f"*... et {len(items) - 20} autres*")
        
        return '\n'.join(parts)
    
    def _markdown_cursor_issues(self, report: AnalysisReport) -> str:
        """Génère la section problèmes de curseurs."""
        issues = report.get_all_cursor_issues()
        if not issues:
            return ""
        
        parts = ['## 🔄 Problèmes de curseurs SQL']
        
        for filepath, issue in issues[:30]:  # Limiter à 30
            severity = issue.get('severity', 'info')
            cursor = issue.get('cursor_name', '?').replace('|', '\\|')
            line = issue.get('line_number', 0)
            msg = issue.get('message', '').replace('|', '\\|')
            file_name = Path(filepath).name
            
            emoji = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}.get(severity, '⚪')
            parts.append(f"- {emoji} **{severity.upper()}** `{file_name}:{line}`")
            parts.append(f"  - Curseur: `{cursor}` - {msg}")
        
        if len(issues) > 30:
            parts.append(f"*... et {len(issues) - 30} autres problèmes*")
        
        return '\n'.join(parts)
    
    def _markdown_memory_issues(self, report: AnalysisReport) -> str:
        """Génère la section problèmes mémoire."""
        issues = report.get_all_memory_issues()
        if not issues:
            return ""
        
        parts = ['## 🧠 Problèmes de gestion mémoire']
        
        # Grouper par sévérité
        by_severity = {'critical': [], 'error': [], 'warning': [], 'info': []}
        for filepath, issue in issues:
            severity = issue.get('severity', 'info')
            by_severity[severity].append((filepath, issue))
        
        for severity in ['critical', 'error', 'warning']:
            items = by_severity[severity]
            if not items:
                continue
            
            emoji = {'critical': '🔴', 'error': '🔴', 'warning': '🟡'}[severity]
            parts.append(f'\n### {emoji} {severity.upper()} ({len(items)})')
            
            for filepath, issue in items[:20]:  # Limiter à 20 par sévérité
                line = issue.get('line_number', 0)
                msg = issue.get('message', '').replace('|', '\\|')
                rec = issue.get('recommendation', '').replace('|', '\\|')
                file_name = Path(filepath).name
                
                parts.append(f"- `{file_name}:{line}` - {msg}")
                if rec:
                    parts.append(f"  - → {rec}")
            
            if len(items) > 20:
                parts.append(f"*... et {len(items) - 20} autres*")
        
        return '\n'.join(parts)
    
    def _complexity_badge(self, value: int, low: int, medium: int) -> str:
        """Retourne un emoji badge selon la complexité."""
        if value <= low:
            return '🟢'
        elif value <= medium:
            return '🟡'
        else:
            return '🔴'
