# guardrails/output_guard.py

"""
Output scanning for Mode 2 code.

The prompt-level guard (Mode 2 system prompt) tells the LLM not to
write destructive code. The output guard is the second line of defense
— it scans the generated code before it is displayed to the analyst.

Defense in depth: the prompt guard catches most cases.
The output guard catches the rest.
"""

import re
from dataclasses import dataclass, field


@dataclass
class CodeScanResult:
    is_safe: bool
    violations: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Definite violations — never allow ───────────────────────────
DANGEROUS_PATTERNS = [
    {
        "pattern": r"\bos\.system\s*\(",
        "severity": "critical",
        "description": "os.system() executes shell commands — potential for arbitrary code execution",
    },
    {
        "pattern": r"\bsubprocess\.(run|call|Popen|check_output)\s*\(",
        "severity": "critical",
        "description": "subprocess calls can execute arbitrary shell commands",
    },
    {
        "pattern": r"\beval\s*\(",
        "severity": "critical",
        "description": "eval() executes arbitrary Python code",
    },
    {
        "pattern": r"\bexec\s*\(",
        "severity": "critical",
        "description": "exec() executes arbitrary Python code",
    },
    {
        "pattern": r"\b__import__\s*\(",
        "severity": "critical",
        "description": "Dynamic imports can load arbitrary modules",
    },
    {
        "pattern": r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX)\b",
        "severity": "critical",
        "description": "SQL DROP statement — irreversible destructive operation",
    },
    {
        "pattern": r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)",
        "severity": "critical",
        "description": "DELETE without WHERE clause — would delete all rows",
    },
    {
        "pattern": r"\bTRUNCATE\s+TABLE\b",
        "severity": "critical",
        "description": "TRUNCATE TABLE — irreversible, removes all rows",
    },
    {
        "pattern": r"\bDROP\s+COLUMN\b",
        "severity": "critical",
        "description": "DROP COLUMN — irreversible schema change",
    },
    {
        "pattern": r"rm\s+-rf?\s+/",
        "severity": "critical",
        "description": "rm -rf on root or absolute path — filesystem destruction",
    },
    {
        "pattern": r"\bopen\s*\(.*['\"]w['\"]",
        "severity": "moderate",
        "description": "File write operation — could overwrite important files",
    },
    {
        "pattern": r"\bshutil\.(rmtree|move|copy)\s*\(",
        "severity": "moderate",
        "description": "shutil file operations — could modify or delete files",
    },
]

# ── Warnings — flag but allow ────────────────────────────────────
WARNING_PATTERNS = [
    {
        "pattern": r"\bUPDATE\b.*\bSET\b",
        "message": "Contains UPDATE statement — verify WHERE clause is present and correct before running",
    },
    {
        "pattern": r"\bINSERT\s+INTO\b",
        "message": "Contains INSERT statement — will write to the database",
    },
    {
        "pattern": r"\bALTER\s+TABLE\b",
        "message": "Contains ALTER TABLE — will modify the schema",
    },
    {
        "pattern": r"\bos\.environ\b",
        "message": "Accesses environment variables — may expose sensitive config",
    },
    {
        "pattern": r"\brequests\.(get|post|put|delete)\s*\(",
        "message": "Makes external HTTP requests — verify the target URL",
    },
]


def scan_code(code: str, language: str = "python") -> CodeScanResult:
    """
    Scan generated code for dangerous patterns.
    Called before displaying Mode 2 output.
    
    Returns CodeScanResult with is_safe=False if any critical
    violations are found. Warnings do not block display.
    """
    if not code or not code.strip():
        return CodeScanResult(is_safe=True)

    violations = []
    warnings = []

    for check in DANGEROUS_PATTERNS:
        pattern = re.compile(check["pattern"], re.IGNORECASE | re.MULTILINE)
        if pattern.search(code):
            violations.append({
                "severity": check["severity"],
                "description": check["description"],
                "pattern": check["pattern"],
            })

    for check in WARNING_PATTERNS:
        pattern = re.compile(check["pattern"], re.IGNORECASE | re.MULTILINE)
        if pattern.search(code):
            warnings.append(check["message"])

    # Critical violations make the result unsafe
    has_critical = any(v["severity"] == "critical" for v in violations)

    return CodeScanResult(
        is_safe=not has_critical,
        violations=violations,
        warnings=warnings,
    )