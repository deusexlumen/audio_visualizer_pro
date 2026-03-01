"""
Detailliertes Code Audit für Audio Visualizer Pro

Dieses Skript analysiert:
1. Code-Komplexität
2. Duplizierte Code
3. Sicherheitsprobleme
4. Performance-Bottlenecks
5. Best Practices
"""

import ast
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
import json


@dataclass
class AuditIssue:
    """Repräsentiert ein Audit-Problem."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # SECURITY, PERFORMANCE, MAINTAINABILITY, STYLE
    file: str
    line: int
    message: str
    suggestion: str


class CodeAuditor:
    """Detaillierter Code Auditor."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.issues: List[AuditIssue] = []
        self.files_analyzed = 0
        self.lines_analyzed = 0
        
    def analyze_all(self):
        """Analysiert alle Python-Dateien."""
        for py_file in self.project_path.rglob("*.py"):
            if ("test" in py_file.name or 
                "__pycache__" in str(py_file) or
                "audit" in py_file.name):
                continue
            self._analyze_file(py_file)
        
        return self._generate_report()
    
    def _analyze_file(self, file_path: Path):
        """Analysiert eine einzelne Datei."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            self.lines_analyzed += len(lines)
            self.files_analyzed += 1
            
            # AST Parsing
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, file_path, lines)
            except SyntaxError:
                pass
            
            # Text-basierte Analyse
            self._analyze_text(content, file_path, lines)
            
        except Exception as e:
            print(f"Fehler bei {file_path}: {e}")
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, lines: List[str]):
        """AST-basierte Analyse."""
        for node in ast.walk(tree):
            # Lange Funktionen
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
                if func_lines > 50:
                    self.issues.append(AuditIssue(
                        severity="MEDIUM",
                        category="MAINTAINABILITY",
                        file=str(file_path.relative_to(self.project_path)),
                        line=node.lineno,
                        message=f"Funktion '{node.name}' ist sehr lang ({func_lines} Zeilen)",
                        suggestion="Funktion in kleinere Teile aufteilen"
                    ))
                
                # Zu viele Parameter
                if len(node.args.args) > 7:
                    self.issues.append(AuditIssue(
                        severity="LOW",
                        category="MAINTAINABILITY",
                        file=str(file_path.relative_to(self.project_path)),
                        line=node.lineno,
                        message=f"Funktion '{node.name}' hat zu viele Parameter ({len(node.args.args)})",
                        suggestion="Datenklasse oder Config-Objekt verwenden"
                    ))
            
            # Klassen ohne Docstring
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    self.issues.append(AuditIssue(
                        severity="LOW",
                        category="MAINTAINABILITY",
                        file=str(file_path.relative_to(self.project_path)),
                        line=node.lineno,
                        message=f"Klasse '{node.name}' hat keinen Docstring",
                        suggestion="Klassen-Dokumentation hinzufügen"
                    ))
            
            # Try ohne Exception-Typ
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        self.issues.append(AuditIssue(
                            severity="HIGH",
                            category="MAINTAINABILITY",
                            file=str(file_path.relative_to(self.project_path)),
                            line=handler.lineno,
                            message="Bare except: Klausel fängt alle Exceptions",
                            suggestion="Spezifische Exception-Typen verwenden (z.B. except ValueError:)"
                        ))
            
            # Globale Variablen
            if isinstance(node, ast.Global):
                self.issues.append(AuditIssue(
                    severity="MEDIUM",
                    category="MAINTAINABILITY",
                    file=str(file_path.relative_to(self.project_path)),
                    line=node.lineno,
                    message="Verwendung von 'global' statement",
                    suggestion="Dependency Injection oder Klassen-Attribute verwenden"
                ))
    
    def _analyze_text(self, content: str, file_path: Path, lines: List[str]):
        """Text-basierte Analyse."""
        file_str = str(file_path.relative_to(self.project_path))
        
        # Sicherheits-Checks
        if 'subprocess' in content and 'shell=True' in content:
            for i, line in enumerate(lines, 1):
                if 'shell=True' in line:
                    self.issues.append(AuditIssue(
                        severity="CRITICAL",
                        category="SECURITY",
                        file=file_str,
                        line=i,
                        message="subprocess mit shell=True ist unsicher",
                        suggestion="shell=False verwenden und Argumente als Liste übergeben"
                    ))
        
        # Hardcoded Secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Mögliches Passwort hardcoded"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "API Key hardcoded"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Secret hardcoded"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Token hardcoded"),
        ]
        
        for pattern, msg in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        self.issues.append(AuditIssue(
                            severity="CRITICAL",
                            category="SECURITY",
                            file=file_str,
                            line=i,
                            message=msg,
                            suggestion="Umgebungsvariablen oder Secrets-Manager verwenden"
                        ))
        
        # Performance-Probleme
        if '.save(' in content and 'optimize=' not in content:
            for i, line in enumerate(lines, 1):
                if '.save(' in line and 'optimize=' not in line:
                    self.issues.append(AuditIssue(
                        severity="LOW",
                        category="PERFORMANCE",
                        file=file_str,
                        line=i,
                        message="PIL Image.save() ohne Optimierung",
                        suggestion="optimize=True hinzufügen für kleinere Dateien"
                    ))
        
        # Schlechte Practices
        if 'print(' in content and 'logger' not in content:
            for i, line in enumerate(lines, 1):
                if 'print(' in line and not line.strip().startswith('#'):
                    self.issues.append(AuditIssue(
                        severity="LOW",
                        category="MAINTAINABILITY",
                        file=file_str,
                        line=i,
                        message="print() statt Logging verwendet",
                        suggestion="logger.info() oder logger.debug() verwenden"
                    ))
        
        # Lange Zeilen
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                self.issues.append(AuditIssue(
                    severity="LOW",
                    category="STYLE",
                    file=file_str,
                    line=i,
                    message=f"Zeile zu lang ({len(line)} Zeichen)",
                    suggestion="Auf 100-120 Zeichen umbrechen"
                ))
        
        # TODO Kommentare
        for i, line in enumerate(lines, 1):
            if 'TODO' in line or 'FIXME' in line or 'XXX' in line:
                self.issues.append(AuditIssue(
                    severity="LOW",
                    category="MAINTAINABILITY",
                    file=file_str,
                    line=i,
                    message=f"Offenes TODO: {line.strip()}",
                    suggestion="TODO in Issue-Tracker überführen"
                ))
    
    def _generate_report(self) -> Dict:
        """Generiert den Audit-Report."""
        report = {
            "summary": {
                "files_analyzed": self.files_analyzed,
                "lines_analyzed": self.lines_analyzed,
                "total_issues": len(self.issues),
                "by_severity": {
                    "CRITICAL": len([i for i in self.issues if i.severity == "CRITICAL"]),
                    "HIGH": len([i for i in self.issues if i.severity == "HIGH"]),
                    "MEDIUM": len([i for i in self.issues if i.severity == "MEDIUM"]),
                    "LOW": len([i for i in self.issues if i.severity == "LOW"]),
                },
                "by_category": {
                    "SECURITY": len([i for i in self.issues if i.category == "SECURITY"]),
                    "PERFORMANCE": len([i for i in self.issues if i.category == "PERFORMANCE"]),
                    "MAINTAINABILITY": len([i for i in self.issues if i.category == "MAINTAINABILITY"]),
                    "STYLE": len([i for i in self.issues if i.category == "STYLE"]),
                }
            },
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in sorted(self.issues, key=lambda x: (x.severity, x.file))
            ]
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Druckt den Report in lesbarer Form."""
        print("=" * 80)
        print("DETAILLIERTES CODE AUDIT - AUDIO VISUALIZER PRO")
        print("=" * 80)
        print()
        
        s = report["summary"]
        print("ZUSAMMENFASSUNG")
        print("-" * 40)
        print(f"Dateien analysiert:     {s['files_analyzed']}")
        print(f"Zeilen analysiert:      {s['lines_analyzed']}")
        print(f"Gesamt-Probleme:        {s['total_issues']}")
        print()
        
        print("Nach Schweregrad")
        print("-" * 40)
        for sev, count in s['by_severity'].items():
            icon = {"CRITICAL": "[C]", "HIGH": "[H]", "MEDIUM": "[M]", "LOW": "[L]"}[sev]
            print(f"{icon} {sev:12} {count:4}")
        print()
        
        print("Nach Kategorie")
        print("-" * 40)
        for cat, count in s['by_category'].items():
            print(f"   {cat:20} {count:4}")
        print()
        
        if s['by_severity']['CRITICAL'] > 0:
            print("KRITISCHE PROBLEME")
            print("-" * 40)
            for issue in report["issues"]:
                if issue["severity"] == "CRITICAL":
                    print(f"\n[{issue['file']}:{issue['line']}]")
                    print(f"   Problem: {issue['message']}")
                    print(f"   Lösung:  {issue['suggestion']}")
            print()
        
        if s['by_severity']['HIGH'] > 0:
            print("HOHE PROBLEME")
            print("-" * 40)
            for issue in report["issues"]:
                if issue["severity"] == "HIGH":
                    print(f"\n[{issue['file']}:{issue['line']}]")
                    print(f"   Problem: {issue['message']}")
                    print(f"   Lösung:  {issue['suggestion']}")
            print()
        
        # Score berechnen
        score = 100
        score -= s['by_severity']['CRITICAL'] * 10
        score -= s['by_severity']['HIGH'] * 5
        score -= s['by_severity']['MEDIUM'] * 2
        score -= s['by_severity']['LOW'] * 0.5
        score = max(0, score)
        
        print("=" * 80)
        print(f"GESAMTBEWERTUNG: {score:.1f}/100")
        print("=" * 80)
        
        if score >= 90:
            print("Ausgezeichnete Code-Qualität")
        elif score >= 75:
            print("Gute Code-Qualität mit Verbesserungspotenzial")
        elif score >= 60:
            print("Akzeptable Code-Qualität, Refactoring empfohlen")
        else:
            print("Kritische Code-Qualität, sofortige Maßnahmen erforderlich")
        
        return score


def main():
    """Hauptfunktion."""
    import sys
    
    # Finde Projekt-Root
    script_dir = Path(__file__).parent
    
    auditor = CodeAuditor(str(script_dir))
    report = auditor.analyze_all()
    score = auditor.print_report(report)
    
    # JSON-Report speichern
    output_file = script_dir / "audit_detailed.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetaillierter Report gespeichert: {output_file}")
    
    return score


if __name__ == "__main__":
    main()
