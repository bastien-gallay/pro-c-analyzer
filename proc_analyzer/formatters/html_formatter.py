"""
Formatter HTML pour les rapports d'analyse.
"""

from datetime import datetime
from pathlib import Path
from html import escape

from ..analyzer import AnalysisReport, FileMetrics, FunctionMetrics


class HTMLFormatter:
    """
    Formatter pour générer des rapports HTML interactifs.
    
    Génère un fichier HTML autonome avec CSS intégré et JavaScript
    minimal pour l'interactivité (tri, filtres).
    """
    
    def format(self, report: AnalysisReport) -> str:
        """
        Formate un rapport en HTML.
        
        Args:
            report: Rapport d'analyse à formater
            
        Returns:
            Chaîne HTML complète
        """
        html_parts = [
            self._html_header(),
            self._html_body_start(),
            self._html_summary(report),
            self._html_files(report),
            self._html_todos(report),
            self._html_cursor_issues(report),
            self._html_memory_issues(report),
            self._html_footer(),
        ]
        return '\n'.join(html_parts)
    
    def save(self, report: AnalysisReport, output_path: str) -> None:
        """
        Sauvegarde un rapport HTML dans un fichier.
        
        Args:
            report: Rapport d'analyse à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        output = Path(output_path)
        output.write_text(self.format(report), encoding='utf-8')
    
    def _html_header(self) -> str:
        """Génère l'en-tête HTML avec CSS."""
        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro*C Static Analyzer - Rapport d'analyse</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #2563eb;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        
        h2 {{
            color: #1e40af;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        h3 {{
            color: #374151;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: #f9fafb;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #2563eb;
        }}
        
        .summary-card h3 {{
            margin-top: 0;
            font-size: 0.9em;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #1e40af;
            margin: 10px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}
        
        th {{
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
            cursor: pointer;
            user-select: none;
        }}
        
        th:hover {{
            background: #e5e7eb;
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        tr:hover {{
            background: #f9fafb;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge-low {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .badge-medium {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .badge-high {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .complexity-low {{
            color: #059669;
            font-weight: 600;
        }}
        
        .complexity-medium {{
            color: #d97706;
            font-weight: 600;
        }}
        
        .complexity-high {{
            color: #dc2626;
            font-weight: 600;
        }}
        
        .file-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f9fafb;
            border-radius: 6px;
        }}
        
        .file-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .file-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: #1e40af;
        }}
        
        .collapsible {{
            background: #f3f4f6;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }}
        
        .collapsible:hover {{
            background: #e5e7eb;
        }}
        
        .collapsible-content {{
            display: none;
        }}
        
        .collapsible-content.active {{
            display: block;
        }}
        
        .issue-list {{
            list-style: none;
            margin: 15px 0;
        }}
        
        .issue-item {{
            padding: 10px;
            margin: 8px 0;
            border-left: 4px solid #e5e7eb;
            background: white;
            border-radius: 4px;
        }}
        
        .issue-item.error {{
            border-left-color: #dc2626;
        }}
        
        .issue-item.warning {{
            border-left-color: #d97706;
        }}
        
        .issue-item.info {{
            border-left-color: #2563eb;
        }}
        
        .issue-location {{
            font-family: monospace;
            font-size: 0.9em;
            color: #6b7280;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }}
    </style>
</head>"""
    
    def _html_body_start(self) -> str:
        """Début du body HTML."""
        return """<body>
    <div class="container">"""
    
    def _html_footer(self) -> str:
        """Pied de page HTML avec JavaScript."""
        return f"""    </div>
    <script>
        // Toggle collapsible sections
        document.querySelectorAll('.collapsible').forEach(button => {{
            button.addEventListener('click', function() {{
                // Le contenu collapsible est le nextElementSibling du parent (file-header)
                const header = this.closest('.file-header');
                const content = header ? header.nextElementSibling : null;
                if (content && content.classList.contains('collapsible-content')) {{
                    content.classList.toggle('active');
                    this.textContent = content.classList.contains('active') ? 'Masquer' : 'Afficher';
                }}
            }});
        }});
        
        // Simple table sorting
        document.querySelectorAll('th').forEach(header => {{
            header.addEventListener('click', function() {{
                const table = this.closest('table');
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const columnIndex = Array.from(this.parentElement.children).indexOf(this);
                const isAsc = this.classList.contains('asc');
                
                // Reset all headers
                table.querySelectorAll('th').forEach(th => th.classList.remove('asc', 'desc'));
                this.classList.add(isAsc ? 'desc' : 'asc');
                
                rows.sort((a, b) => {{
                    const aText = a.children[columnIndex].textContent.trim();
                    const bText = b.children[columnIndex].textContent.trim();
                    const aNum = parseFloat(aText);
                    const bNum = parseFloat(bText);
                    
                    if (!isNaN(aNum) && !isNaN(bNum)) {{
                        return isAsc ? bNum - aNum : aNum - bNum;
                    }}
                    return isAsc ? bText.localeCompare(aText) : aText.localeCompare(bText);
                }});
                
                rows.forEach(row => tbody.appendChild(row));
            }});
        }});
    </script>
</body>
</html>"""
    
    def _html_summary(self, report: AnalysisReport) -> str:
        """Génère la section résumé."""
        return f"""        <h1>Pro*C Static Analyzer - Rapport d'analyse</h1>
        <p style="color: #6b7280; margin-bottom: 30px;">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
        
        <h2>Résumé</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Fichiers analysés</h3>
                <div class="value">{report.total_files}</div>
            </div>
            <div class="summary-card">
                <h3>Fonctions totales</h3>
                <div class="value">{report.total_functions}</div>
            </div>
            <div class="summary-card">
                <h3>Lignes de code</h3>
                <div class="value">{report.total_lines:,}</div>
            </div>
            <div class="summary-card">
                <h3>Complexité cyclomatique moyenne</h3>
                <div class="value">{report.avg_cyclomatic:.2f}</div>
            </div>
            <div class="summary-card">
                <h3>Complexité cognitive moyenne</h3>
                <div class="value">{report.avg_cognitive:.2f}</div>
            </div>
            <div class="summary-card">
                <h3>TODO/FIXME</h3>
                <div class="value">{report.total_todos}</div>
            </div>
            <div class="summary-card">
                <h3>Problèmes curseurs</h3>
                <div class="value">{report.total_cursor_issues}</div>
            </div>
            <div class="summary-card">
                <h3>Problèmes mémoire</h3>
                <div class="value">{report.total_memory_issues}</div>
            </div>
        </div>"""
    
    def _html_files(self, report: AnalysisReport) -> str:
        """Génère la section des fichiers."""
        if not report.files:
            return ""
        
        parts = ['<h2>Fichiers analysés</h2>']
        
        for file_metrics in report.files:
            parts.append(self._html_file_section(file_metrics))
        
        return '\n'.join(parts)
    
    def _html_file_section(self, metrics: FileMetrics) -> str:
        """Génère la section HTML pour un fichier."""
        file_name = Path(metrics.filepath).name
        parts = [
            f'<div class="file-section">',
            f'<div class="file-header">',
            f'<div class="file-title">📄 {escape(file_name)}</div>',
            f'<button class="collapsible">Afficher</button>',
            f'</div>',
            f'<div class="collapsible-content">',
        ]
        
        # Stats générales
        parts.append('<p>')
        parts.append(f'<strong>Lignes:</strong> {metrics.total_lines} (non vides: {metrics.non_empty_lines})<br>')
        parts.append(f'<strong>Fonctions:</strong> {metrics.function_count}<br>')
        parts.append(f'<strong>Blocs SQL:</strong> {metrics.total_sql_blocks}<br>')
        if metrics.todos:
            high_todos = sum(1 for t in metrics.todos if t.get('priority') == 'high')
            parts.append(f'<strong>TODO/FIXME:</strong> {len(metrics.todos)} ({high_todos} haute priorité)<br>')
        parts.append('</p>')
        
        # Tableau des fonctions
        if metrics.functions:
            parts.append('<h3>Fonctions</h3>')
            parts.append('<table>')
            parts.append('<thead><tr>')
            parts.append('<th>Fonction</th><th>Lignes</th><th>Cyclo</th><th>Cogn</th><th>SQL</th>')
            parts.append('</tr></thead>')
            parts.append('<tbody>')
            
            for func in metrics.functions:
                cyclo_class = self._complexity_class(func.cyclomatic_complexity, 5, 10)
                cogn_class = self._complexity_class(func.cognitive_complexity, 8, 15)
                
                parts.append('<tr>')
                parts.append(f'<td><code>{escape(func.name)}</code> (L{func.start_line})</td>')
                parts.append(f'<td>{func.line_count}</td>')
                parts.append(f'<td class="{cyclo_class}">{func.cyclomatic_complexity}</td>')
                parts.append(f'<td class="{cogn_class}">{func.cognitive_complexity}</td>')
                parts.append(f'<td>{func.sql_blocks_count}</td>')
                parts.append('</tr>')
            
            parts.append('</tbody></table>')
        
        # TODOs pour ce fichier
        if metrics.todos:
            parts.append('<h3>📝 TODO/FIXME</h3>')
            parts.append('<ul class="issue-list">')
            
            # Grouper par priorité
            by_priority = {'high': [], 'medium': [], 'low': []}
            for todo in metrics.todos:
                priority = todo.get('priority', 'low')
                by_priority[priority].append(todo)
            
            for priority in ['high', 'medium', 'low']:
                items = by_priority[priority]
                if not items:
                    continue
                
                badge_class = f'badge-{priority}'
                for todo in items:
                    tag = todo.get('tag', 'TODO')
                    msg = escape(todo.get('message', ''))
                    line = todo.get('line_number', 0)
                    
                    parts.append('<li class="issue-item">')
                    parts.append(f'<span class="badge {badge_class}">{priority.upper()}</span> ')
                    parts.append(f'<strong>{tag}</strong> <span class="issue-location">L{line}</span><br>')
                    parts.append(f'{msg}')
                    parts.append('</li>')
            
            parts.append('</ul>')
        
        # Problèmes de curseurs pour ce fichier
        if metrics.cursor_analysis and metrics.cursor_analysis.get('issues'):
            issues = metrics.cursor_analysis['issues']
            if issues:
                parts.append('<h3>🔄 Problèmes de curseurs SQL</h3>')
                parts.append('<ul class="issue-list">')
                
                for issue in issues[:20]:  # Limiter à 20
                    severity = issue.get('severity', 'info')
                    cursor = escape(issue.get('cursor_name', '?'))
                    line = issue.get('line_number', 0)
                    msg = escape(issue.get('message', ''))
                    
                    parts.append(f'<li class="issue-item {severity}">')
                    parts.append(f'<strong>{severity.upper()}</strong> <span class="issue-location">L{line}</span><br>')
                    parts.append(f'Curseur: <code>{cursor}</code> - {msg}')
                    parts.append('</li>')
                
                if len(issues) > 20:
                    parts.append(f'<li><em>... et {len(issues) - 20} autres problèmes</em></li>')
                
                parts.append('</ul>')
        
        # Problèmes mémoire pour ce fichier
        if metrics.memory_analysis and metrics.memory_analysis.get('issues'):
            issues = metrics.memory_analysis['issues']
            if issues:
                parts.append('<h3>🧠 Problèmes de gestion mémoire</h3>')
                
                # Grouper par sévérité
                by_severity = {'critical': [], 'error': [], 'warning': [], 'info': []}
                for issue in issues:
                    severity = issue.get('severity', 'info')
                    by_severity[severity].append(issue)
                
                for severity in ['critical', 'error', 'warning']:
                    items = by_severity[severity]
                    if not items:
                        continue
                    
                    parts.append(f'<h4><span class="badge badge-{severity}">{severity.upper()}</span> ({len(items)})</h4>')
                    parts.append('<ul class="issue-list">')
                    
                    for issue in items[:15]:  # Limiter à 15 par sévérité
                        line = issue.get('line_number', 0)
                        msg = escape(issue.get('message', ''))
                        rec = escape(issue.get('recommendation', ''))
                        
                        parts.append(f'<li class="issue-item {severity}">')
                        parts.append(f'<span class="issue-location">L{line}</span><br>')
                        parts.append(f'{msg}')
                        if rec:
                            parts.append(f'<br><em>→ {rec}</em>')
                        parts.append('</li>')
                    
                    if len(items) > 15:
                        parts.append(f'<li><em>... et {len(items) - 15} autres</em></li>')
                    
                    parts.append('</ul>')
        
        parts.extend(['</div>', '</div>'])
        return '\n'.join(parts)
    
    def _html_todos(self, report: AnalysisReport) -> str:
        """Génère la section TODOs."""
        todos = report.get_all_todos()
        if not todos:
            return ""
        
        parts = ['<h2>TODO/FIXME</h2>']
        
        # Grouper par priorité
        by_priority = {'high': [], 'medium': [], 'low': []}
        for filepath, todo in todos:
            priority = todo.get('priority', 'low')
            by_priority[priority].append((filepath, todo))
        
        for priority in ['high', 'medium', 'low']:
            items = by_priority[priority]
            if not items:
                continue
            
            badge_class = f'badge-{priority}'
            parts.append(f'<h3><span class="badge {badge_class}">{priority.upper()}</span> ({len(items)})</h3>')
            parts.append('<ul class="issue-list">')
            
            for filepath, todo in items:
                tag = todo.get('tag', 'TODO')
                msg = escape(todo.get('message', ''))
                line = todo.get('line_number', 0)
                file_name = Path(filepath).name
                
                parts.append('<li class="issue-item">')
                parts.append(f'<strong>{tag}</strong> <span class="issue-location">{file_name}:{line}</span><br>')
                parts.append(f'{msg}')
                parts.append('</li>')
            
            parts.append('</ul>')
        
        return '\n'.join(parts)
    
    def _html_cursor_issues(self, report: AnalysisReport) -> str:
        """Génère la section problèmes de curseurs."""
        issues = report.get_all_cursor_issues()
        if not issues:
            return ""
        
        parts = ['<h2>Problèmes de curseurs SQL</h2>', '<ul class="issue-list">']
        
        for filepath, issue in issues[:50]:  # Limiter à 50
            severity = issue.get('severity', 'info')
            cursor = escape(issue.get('cursor_name', '?'))
            line = issue.get('line_number', 0)
            msg = escape(issue.get('message', ''))
            file_name = Path(filepath).name
            
            parts.append(f'<li class="issue-item {severity}">')
            parts.append(f'<strong>{severity.upper()}</strong> <span class="issue-location">{file_name}:{line}</span><br>')
            parts.append(f'Curseur: <code>{cursor}</code> - {msg}')
            parts.append('</li>')
        
        if len(issues) > 50:
            parts.append(f'<li><em>... et {len(issues) - 50} autres problèmes</em></li>')
        
        parts.append('</ul>')
        return '\n'.join(parts)
    
    def _html_memory_issues(self, report: AnalysisReport) -> str:
        """Génère la section problèmes mémoire."""
        issues = report.get_all_memory_issues()
        if not issues:
            return ""
        
        parts = ['<h2>Problèmes de gestion mémoire</h2>']
        
        # Grouper par sévérité
        by_severity = {'critical': [], 'error': [], 'warning': [], 'info': []}
        for filepath, issue in issues:
            severity = issue.get('severity', 'info')
            by_severity[severity].append((filepath, issue))
        
        for severity in ['critical', 'error', 'warning']:
            items = by_severity[severity]
            if not items:
                continue
            
            parts.append(f'<h3><span class="badge badge-{severity}">{severity.upper()}</span> ({len(items)})</h3>')
            parts.append('<ul class="issue-list">')
            
            for filepath, issue in items[:30]:  # Limiter à 30 par sévérité
                line = issue.get('line_number', 0)
                msg = escape(issue.get('message', ''))
                rec = escape(issue.get('recommendation', ''))
                file_name = Path(filepath).name
                
                parts.append(f'<li class="issue-item {severity}">')
                parts.append(f'<span class="issue-location">{file_name}:{line}</span><br>')
                parts.append(f'{msg}')
                if rec:
                    parts.append(f'<br><em>→ {rec}</em>')
                parts.append('</li>')
            
            if len(items) > 30:
                parts.append(f'<li><em>... et {len(items) - 30} autres</em></li>')
            
            parts.append('</ul>')
        
        return '\n'.join(parts)
    
    def _complexity_class(self, value: int, low: int, medium: int) -> str:
        """Retourne la classe CSS selon la complexité."""
        if value <= low:
            return 'complexity-low'
        elif value <= medium:
            return 'complexity-medium'
        else:
            return 'complexity-high'
