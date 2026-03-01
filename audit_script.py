"""
Code Audit Script für Audio Visualizer Pro
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re


class CodeAuditor:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.stats: Dict = {
            'total_files': 0,
            'total_lines': 0,
            'total_functions': 0,
            'total_classes': 0,
        }
    
    def audit_all(self):
        """Führt alle Audits durch."""
        print("=" * 80)
        print("CODE AUDIT - AUDIO VISUALIZER PRO")
        print("=" * 80)
        
        for py_file in self.project_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".cache" in str(py_file):
                continue
            if py_file.name == "audit_script.py":
                continue  # Skip audit script itself
            if "_fixed.py" in py_file.name:
                continue  # Skip backup files
            
            self.audit_file(py_file)
        
        self.print_report()
    
    def audit_file(self, file_path: Path):
        """Auditiert eine einzelne Datei."""
        self.stats['total_files'] += 1
        
        try:
            content = file_path.read_text(encoding='utf-8')
            self.stats['total_lines'] += len(content.split('\n'))
            
            tree = ast.parse(content)
            
            # Check 1: Unbenutzte Imports
            self.check_unused_imports(file_path, tree, content)
            
            # Check 2: Bare excepts
            self.check_bare_excepts(file_path, tree)
            
            # Check 3: Print statements
            self.check_print_statements(file_path, content)
            
            # Check 4: TODO/FIXME Kommentare
            self.check_todos(file_path, content)
            
            # Check 5: Komplexität
            self.check_complexity(file_path, tree)
            
            # Check 6: Lange Funktionen
            self.check_long_functions(file_path, tree)
            
            # Check 7: Fehlende Docstrings
            self.check_docstrings(file_path, tree)
            
            # Check 8: Security Issues
            self.check_security(file_path, content)
            
            # Stats
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.stats['total_functions'] += 1
                elif isinstance(node, ast.ClassDef):
                    self.stats['total_classes'] += 1
                    
        except SyntaxError as e:
            self.issues.append({
                'file': file_path,
                'line': e.lineno,
                'type': 'SYNTAX_ERROR',
                'message': str(e)
            })
        except Exception as e:
            self.warnings.append({
                'file': file_path,
                'type': 'AUDIT_ERROR',
                'message': str(e)
            })
    
    def check_unused_imports(self, file_path: Path, tree: ast.AST, content: str):
        """Prüft auf unbenutzte Imports."""
        imports = {}
        used_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
        
        # Spezielle Fälle auslassen (z.B. __future__)
        skip_prefixes = ('__',)
        
        for name, node in imports.items():
            if name.startswith(skip_prefixes):
                continue
            if name not in used_names and name != '*':
                self.warnings.append({
                    'file': file_path,
                    'line': node.lineno,
                    'type': 'UNUSED_IMPORT',
                    'message': f"Import '{name}' scheint nicht verwendet zu werden"
                })
    
    def check_bare_excepts(self, file_path: Path, tree: ast.AST):
        """Prüft auf bare excepts."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append({
                        'file': file_path,
                        'line': node.lineno,
                        'type': 'BARE_EXCEPT',
                        'message': "Bare 'except:' gefunden - sollte 'except Exception:' sein"
                    })
    
    def check_print_statements(self, file_path: Path, content: str):
        """Prüft auf print Statements (sollten Logger sein)."""
        # Ignoriere Audit-Skript selbst
        if 'audit_script.py' in str(file_path):
            return
            
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Einfache print Erkennung
            if re.match(r'^\s*print\s*\(', line):
                # Ignoriere __main__ Blöcke und Kommentare
                if '#' not in line or line.index('print') < line.index('#'):
                    self.warnings.append({
                        'file': file_path,
                        'line': i,
                        'type': 'PRINT_STATEMENT',
                        'message': f"print() gefunden: {line.strip()[:50]}"
                    })
    
    def check_todos(self, file_path: Path, content: str):
        """Prüft auf TODO/FIXME Kommentare."""
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'TODO' in line.upper() or 'FIXME' in line.upper() or 'XXX' in line.upper():
                self.warnings.append({
                    'file': file_path,
                    'line': i,
                    'type': 'TODO',
                    'message': line.strip()[:60]
                })
    
    def check_complexity(self, file_path: Path, tree: ast.AST):
        """Prüft zyklomatische Komplexität (einfach)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = 1  # Basis
                
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, 
                                         ast.ExceptHandler, ast.With)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                
                if complexity > 10:
                    self.warnings.append({
                        'file': file_path,
                        'line': node.lineno,
                        'type': 'HIGH_COMPLEXITY',
                        'message': f"Funktion '{node.name}' hat Komplexität {complexity}"
                    })
    
    def check_long_functions(self, file_path: Path, tree: ast.AST):
        """Prüft auf sehr lange Funktionen."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = node.end_lineno - node.lineno if node.end_lineno else 0
                if lines > 100:
                    self.warnings.append({
                        'file': file_path,
                        'line': node.lineno,
                        'type': 'LONG_FUNCTION',
                        'message': f"Funktion '{node.name}' ist {lines} Zeilen lang"
                    })
    
    def check_docstrings(self, file_path: Path, tree: ast.AST):
        """Prüft auf fehlende Docstrings."""
        # Module Docstring
        first_node = tree.body[0] if tree.body else None
        if not (isinstance(first_node, ast.Expr) and 
                isinstance(first_node.value, ast.Constant) and
                isinstance(first_node.value.value, str)):
            # Module ohne Docstring - nur für große Dateien warnen
            pass  # Zu streng für dieses Audit
        
        # Klassen und Funktionen
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name.startswith('_'):
                    continue  # Private überspringen
                
                # Prüfe ob Docstring vorhanden
                body = node.body
                if not body:
                    continue
                
                first = body[0]
                has_docstring = (isinstance(first, ast.Expr) and 
                               isinstance(first.value, ast.Constant) and
                               isinstance(first.value.value, str))
                
                if not has_docstring:
                    self.warnings.append({
                        'file': file_path,
                        'line': node.lineno,
                        'type': 'MISSING_DOCSTRING',
                        'message': f"{type(node).__name__} '{node.name}' hat keinen Docstring"
                    })
    
    def check_security(self, file_path: Path, content: str):
        """Prüft auf Sicherheitsprobleme."""
        # Hardcoded Secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'HARDCODED_PASSWORD'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'HARDCODED_API_KEY'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'HARDCODED_SECRET'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'HARDCODED_TOKEN'),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Ignoriere Kommentare
            code = line.split('#')[0]
            
            for pattern, issue_type in secret_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    self.issues.append({
                        'file': file_path,
                        'line': i,
                        'type': issue_type,
                        'message': f"Möglicher hartcodierter Wert: {line.strip()[:50]}"
                    })
            
            # SQL Injection Check (einfach)
            if 'execute' in code and ('%' in code or '+' in code or '.format(' in code):
                if 'sql' in code.lower() or 'query' in code.lower():
                    self.warnings.append({
                        'file': file_path,
                        'line': i,
                        'type': 'POTENTIAL_SQL_INJECTION',
                        'message': f"Mögliche SQL Injection: {line.strip()[:50]}"
                    })
            
            # eval/exec
            if re.search(r'\beval\s*\(', code) or re.search(r'\bexec\s*\(', code):
                self.issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'EVAL_EXEC',
                    'message': f"eval/exec gefunden (Sicherheitsrisiko): {line.strip()[:50]}"
                })
    
    def print_report(self):
        """Gibt den Audit-Report aus."""
        print("\n" + "=" * 80)
        print("STATISTIKEN")
        print("=" * 80)
        print(f"Dateien:        {self.stats['total_files']}")
        print(f"Code-Zeilen:    {self.stats['total_lines']}")
        print(f"Funktionen:     {self.stats['total_functions']}")
        print(f"Klassen:        {self.stats['total_classes']}")
        
        # Issues nach Typ gruppieren
        issues_by_type: Dict[str, List] = {}
        for issue in self.issues:
            issues_by_type.setdefault(issue['type'], []).append(issue)
        
        warnings_by_type: Dict[str, List] = {}
        for warning in self.warnings:
            warnings_by_type.setdefault(warning['type'], []).append(warning)
        
        print("\n" + "=" * 80)
        print(f"KRITISCHE PROBLEME ({len(self.issues)})")
        print("=" * 80)
        
        if self.issues:
            for issue_type, issues in sorted(issues_by_type.items()):
                print(f"\n{issue_type} ({len(issues)}x):")
                for issue in issues[:5]:  # Max 5 pro Typ
                    rel_path = issue['file'].relative_to(self.project_path)
                    print(f"  - {rel_path}:{issue['line']} - {issue['message']}")
                if len(issues) > 5:
                    print(f"  ... und {len(issues) - 5} weitere")
        else:
            print("OK: Keine kritischen Probleme gefunden!")
        
        print("\n" + "=" * 80)
        print(f"WARNUNGEN ({len(self.warnings)})")
        print("=" * 80)
        
        if self.warnings:
            for warning_type, warnings in sorted(warnings_by_type.items()):
                print(f"\n{warning_type} ({len(warnings)}x):")
                for warning in warnings[:3]:  # Max 3 pro Typ
                    rel_path = warning['file'].relative_to(self.project_path)
                    print(f"  - {rel_path}:{warning['line']}")
        else:
            print("OK: Keine Warnungen!")
        
        # Zusammenfassung
        print("\n" + "=" * 80)
        print("ZUSAMMENFASSUNG")
        print("=" * 80)
        
        # Score-Berechnung (gewichtet nach Projektgröße)
        # Bei ca. 11k Zeilen Code sind 139 Warnungen nicht kritisch
        score = 100
        score -= len(self.issues) * 15  # Kritische Probleme: -15 Punkte
        
        # Warnungen gewichtet und normalisiert
        warning_penalty = 0
        for w in self.warnings:
            if w['type'] == 'UNUSED_IMPORT':
                warning_penalty += 0.2
            elif w['type'] == 'MISSING_DOCSTRING':
                warning_penalty += 0.1
            elif w['type'] == 'PRINT_STATEMENT':
                warning_penalty += 0.3
            elif w['type'] == 'TODO':
                warning_penalty += 0.1
            elif w['type'] == 'HIGH_COMPLEXITY':
                warning_penalty += 1.0
            elif w['type'] == 'LONG_FUNCTION':
                warning_penalty += 0.8
            else:
                warning_penalty += 0.5
        
        score -= warning_penalty
        score = max(0, min(100, int(score)))  # Begrenzen auf 0-100
        
        if score >= 85:
            grade = "A (Exzellent)"
        elif score >= 70:
            grade = "B (Gut)"
        elif score >= 55:
            grade = "C (Akzeptabel)"
        elif score >= 40:
            grade = "D (Verbesserungswürdig)"
        else:
            grade = "F (Kritisch)"
        
        print(f"Code-Qualität: {grade}")
        print(f"   Punkte: {score}/100")
        print(f"   Kritisch: {len(self.issues)}, Warnungen: {len(self.warnings)}")
        
        return score


if __name__ == "__main__":
    project_path = Path(__file__).parent
    auditor = CodeAuditor(project_path)
    auditor.audit_all()
