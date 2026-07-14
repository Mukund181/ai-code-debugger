"""
Multi-language AST / structural parser for the Repository Analyzer.

Supports:
  - Python (.py)          — full AST parsing via stdlib `ast`
  - Jupyter Notebooks (.ipynb) — cell extraction + Python AST
  - JavaScript / TypeScript (.js, .jsx, .ts, .tsx) — regex
  - Java (.java)          — regex
  - C / C++ (.c, .cpp, .h, .hpp, .cc, .cxx) — regex
  - Go (.go)              — regex
  - Ruby (.rb)            — regex
  - Generic text (PHP, C#, SQL, Shell, HTML, CSS, JSON, Markdown, YAML) — fallback

Every parser returns the same dict shape:
  { "imports": [...], "classes": {...}, "functions": {...}, "raw_code": str }
so that graph_rag.py can consume them uniformly.
"""

import ast
import os
import re
import json

# ---------------------------------------------------------------------------
# Extension registry
# ---------------------------------------------------------------------------

PYTHON_EXTENSIONS  = {".py"}
NOTEBOOK_EXTENSION = {".ipynb"}
JS_EXTENSIONS      = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
JAVA_EXTENSIONS    = {".java"}
C_EXTENSIONS       = {".c", ".cpp", ".h", ".hpp", ".cc", ".cxx"}
GO_EXTENSIONS      = {".go"}
RUBY_EXTENSIONS    = {".rb"}

# Generic and text-based extensions to enable broad codebase scanning
GENERIC_EXTENSIONS = {
    ".html", ".css", ".php", ".cs", ".sh", ".sql", ".json", 
    ".md", ".yml", ".yaml", ".txt", ".ini", ".conf", ".xml"
}

ALL_SOURCE_EXTENSIONS = (
    PYTHON_EXTENSIONS | NOTEBOOK_EXTENSION |
    JS_EXTENSIONS | JAVA_EXTENSIONS |
    C_EXTENSIONS | GO_EXTENSIONS | RUBY_EXTENSIONS |
    GENERIC_EXTENSIONS
)

# Directories to always skip during filesystem walks
SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    "env", ".env", "dist", "build", ".next", ".tox",
    ".mypy_cache", ".pytest_cache", ".eggs", "egg-info",
}

def get_all_source_extensions() -> set:
    """Returns the full set of file extensions we can parse."""
    return ALL_SOURCE_EXTENSIONS


def should_skip_dir(dirname: str) -> bool:
    """Returns True if a directory should be skipped during scanning."""
    lower = dirname.lower()
    return lower in SKIP_DIRS or lower.endswith(".egg-info")


# ===================================================================
#  PYTHON PARSER  (AST-based, full fidelity)
# ===================================================================

def clean_ipython_magics(code_content: str) -> str:
    """Comments out IPython magics (lines starting with % or !) so Python's AST parser doesn't crash."""
    cleaned_lines = []
    for line in code_content.splitlines():
        stripped = line.strip()
        if stripped.startswith(("%", "!")):
            cleaned_lines.append("# " + line)
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def parse_python_fallback(code_content: str, filename: str = "<unknown>") -> dict:
    """Regex-based fallback for Python files that fail AST parsing (e.g. placeholder config values)."""
    result = {
        "imports": [],
        "classes": {},
        "functions": {},
        "raw_code": code_content,
    }

    for m in re.finditer(r'^from\s+([\w.]+)\s+import\s+(.+)$', code_content, re.MULTILINE):
        module = m.group(1)
        for name in m.group(2).split(","):
            name = name.strip().split(" as ")[0].strip()
            if name and name != "(":
                result["imports"].append(f"{module}.{name}" if name != "*" else module)

    for m in re.finditer(r'^import\s+([\w.]+(?:\s*,\s*[\w.]+)*)', code_content, re.MULTILINE):
        for name in m.group(1).split(","):
            name = name.strip().split(" as ")[0].strip()
            if name:
                result["imports"].append(name)

    for m in re.finditer(r'^class\s+(\w+)(?:\(([^)]*)\))?\s*:', code_content, re.MULTILINE):
        cls_name = m.group(1)
        bases_str = m.group(2) or ""
        bases = [b.strip() for b in bases_str.split(",") if b.strip()]
        class_start = m.end()
        methods = {}
        for mm in re.finditer(r'^\s+(?:async\s+)?def\s+(\w+)\s*\(', code_content[class_start:], re.MULTILINE):
            mname = mm.group(1)
            body_start = class_start + mm.start()
            body_snippet = code_content[body_start:body_start + 500]
            methods[mname] = {
                "calls": _extract_function_calls(body_snippet),
                "line_start": code_content[:body_start].count("\n") + 1,
                "line_end": code_content[:body_start].count("\n") + 5,
                "docstring": "",
            }
        result["classes"][cls_name] = {
            "bases": bases,
            "methods": methods,
            "line_start": code_content[:m.start()].count("\n") + 1,
            "line_end": code_content[:m.end()].count("\n") + 1,
            "docstring": "",
        }

    for m in re.finditer(r'^(?:async\s+)?def\s+(\w+)\s*\(', code_content, re.MULTILINE):
        fname = m.group(1)
        if fname in result["functions"]:
            continue
        body_snippet = code_content[m.start():m.start() + 500]
        result["functions"][fname] = {
            "calls": _extract_function_calls(body_snippet),
            "line_start": code_content[:m.start()].count("\n") + 1,
            "line_end": code_content[:m.start()].count("\n") + 5,
            "docstring": "",
        }

    result["imports"] = list(set(result["imports"]))
    return result


def parse_code(code_content: str, filename: str = "<unknown>") -> dict:
    """Parses Python code using AST to find defined classes, functions, calls and imports."""
    cleaned_code = clean_ipython_magics(code_content)
    try:
        tree = ast.parse(cleaned_code, filename=filename)
    except Exception as e:
        fallback = parse_python_fallback(cleaned_code, filename)
        fallback["parse_warning"] = f"AST parse failed, used regex fallback: {str(e)}"
        return fallback

    result = {
        "imports": [],
        "classes": {},
        "functions": {},
        "raw_code": code_content
    }

    def extract_calls(node):
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    parts = []
                    curr = child.func
                    while isinstance(curr, ast.Attribute):
                        parts.append(curr.attr)
                        curr = curr.value
                    if isinstance(curr, ast.Name):
                        parts.append(curr.id)
                    parts.reverse()
                    calls.append(".".join(parts))
        return list(set(calls))

    for node in tree.body:
        if isinstance(node, ast.Import):
            for name in node.names:
                result["imports"].append(name.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for name in node.names:
                result["imports"].append(f"{module}.{name.name}" if module else name.name)
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            class_info = {
                "bases": bases,
                "methods": {},
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
                "docstring": ast.get_docstring(node) or ""
            }
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_name = child.name
                    class_info["methods"][method_name] = {
                        "calls": extract_calls(child),
                        "line_start": child.lineno,
                        "line_end": getattr(child, "end_lineno", child.lineno),
                        "docstring": ast.get_docstring(child) or ""
                    }
            result["classes"][class_name] = class_info
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = node.name
            result["functions"][func_name] = {
                "calls": extract_calls(node),
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
                "docstring": ast.get_docstring(node) or ""
            }

    return result


def parse_file(file_path: str) -> dict:
    """Reads a local Python file and parses its AST structure."""
    if not os.path.exists(file_path):
        return {"error": f"File does not exist: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return parse_code(content, filename=os.path.basename(file_path))
    except Exception as e:
        return {"error": f"Reading file failed: {str(e)}"}


def parse_ipynb_file(file_path: str) -> dict:
    """Reads a Jupyter Notebook, extracts code cells, and parses via Python AST."""
    if not os.path.exists(file_path):
        return {"error": f"File does not exist: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            notebook_data = json.load(f)
        code_cells = []
        for cell in notebook_data.get("cells", []):
            if cell.get("cell_type") == "code":
                source = cell.get("source", "")
                if isinstance(source, list):
                    code_cells.append("".join(source))
                elif isinstance(source, str):
                    code_cells.append(source)
        full_code = "\n\n# --- JUPYTER CELL ---\n\n".join(code_cells)
        return parse_code(full_code, filename=os.path.basename(file_path))
    except Exception as e:
        return {"error": f"Reading/parsing Jupyter Notebook failed: {str(e)}"}


# ===================================================================
#  GENERIC REGEX-BASED PARSER  (JS/TS, Java, C/C++, Go, Ruby)
# ===================================================================

def _extract_function_calls(body: str) -> list:
    """Extracts function call names from a code body using a simple regex."""
    calls = re.findall(r'(?<!\w)([a-zA-Z_][\w.]*)\s*\(', body)
    keywords = {
        "if", "else", "for", "while", "switch", "case", "return", "new",
        "try", "catch", "throw", "throws", "finally", "typeof", "instanceof",
        "sizeof", "delete", "void", "this", "super", "self", "print",
        "println", "printf", "fmt", "log", "console", "require", "import",
        "export", "from", "package", "module", "class", "struct", "enum",
        "interface", "func", "def", "do", "end", "begin", "rescue",
        "ensure", "yield", "raise", "puts", "attr_accessor", "attr_reader",
    }
    return list(set(c for c in calls if c not in keywords and not c.startswith(".")))


def _extract_generic_imports(code: str, ext: str) -> list:
    """Extracts reference dependencies for general programming configurations (PHP, C#, Shell)."""
    imports = []
    if ext == ".php":
        for m in re.finditer(r'''(?:require|include)(?:_once)?\s*\(?\s*['"](.+?)['"]''', code):
            imports.append(m.group(1))
        for m in re.finditer(r'''use\s+([\w\\_]+)\s*;''', code):
            imports.append(m.group(1))
    elif ext == ".cs":
        for m in re.finditer(r'''using\s+([\w.]+)\s*;''', code):
            imports.append(m.group(1))
    elif ext in (".sh", ".bash"):
        for m in re.finditer(r'''(?:source|\.)\s+([\w./-]+)''', code):
            imports.append(m.group(1))
    return list(set(imports))


def parse_js_ts(code: str, filename: str = "<unknown>") -> dict:
    """Regex-based parser for JavaScript / TypeScript files."""
    result = {"imports": [], "classes": {}, "functions": {}, "raw_code": code}

    # ES6 imports
    for m in re.finditer(r'''import\s+.*?\s+from\s+['"](.+?)['"]''', code):
        result["imports"].append(m.group(1))
    # CommonJS require
    for m in re.finditer(r'''require\s*\(\s*['"](.+?)['"]\s*\)''', code):
        result["imports"].append(m.group(1))

    # Classes
    for m in re.finditer(r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{', code):
        cls_name = m.group(1)
        bases = [m.group(2)] if m.group(2) else []
        start = m.end()
        methods = {}
        for mm in re.finditer(r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', code[start:]):
            mname = mm.group(1)
            if mname not in ("if", "for", "while", "switch", "catch"):
                methods[mname] = {
                    "calls": _extract_function_calls(code[start + mm.start():start + mm.end() + 200]),
                    "line_start": code[:start + mm.start()].count('\n') + 1,
                    "line_end": code[:start + mm.end()].count('\n') + 1,
                    "docstring": ""
                }
        result["classes"][cls_name] = {
            "bases": bases, "methods": methods,
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.end()].count('\n') + 1,
            "docstring": ""
        }

    # Top-level functions
    for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(', code):
        fname = m.group(1)
        body_snippet = code[m.start():m.start() + 500]
        result["functions"][fname] = {
            "calls": _extract_function_calls(body_snippet),
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.start()].count('\n') + 5,
            "docstring": ""
        }
    # Arrow const functions
    for m in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(?', code):
        fname = m.group(1)
        if fname not in result["functions"]:
            body_snippet = code[m.start():m.start() + 500]
            result["functions"][fname] = {
                "calls": _extract_function_calls(body_snippet),
                "line_start": code[:m.start()].count('\n') + 1,
                "line_end": code[:m.start()].count('\n') + 5,
                "docstring": ""
            }

    return result


def parse_java(code: str, filename: str = "<unknown>") -> dict:
    """Regex-based parser for Java files."""
    result = {"imports": [], "classes": {}, "functions": {}, "raw_code": code}

    for m in re.finditer(r'import\s+([\w.*]+)\s*;', code):
        result["imports"].append(m.group(1))

    for m in re.finditer(
        r'(?:public|private|protected)?\s*(?:abstract\s+)?(?:static\s+)?class\s+(\w+)'
        r'(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*\{', code
    ):
        cls_name = m.group(1)
        bases = []
        if m.group(2):
            bases.append(m.group(2))
        if m.group(3):
            bases.extend(b.strip() for b in m.group(3).split(","))
        methods = {}
        class_start = m.end()
        for mm in re.finditer(
            r'(?:public|private|protected)?\s*(?:static\s+)?(?:abstract\s+)?'
            r'(?:[\w<>\[\]]+)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{', code[class_start:]
        ):
            mname = mm.group(1)
            methods[mname] = {
                "calls": _extract_function_calls(code[class_start + mm.start():class_start + mm.end() + 300]),
                "line_start": code[:class_start + mm.start()].count('\n') + 1,
                "line_end": code[:class_start + mm.end()].count('\n') + 1,
                "docstring": ""
            }
        result["classes"][cls_name] = {
            "bases": bases, "methods": methods,
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.end()].count('\n') + 1,
            "docstring": ""
        }

    return result


def parse_c_cpp(code: str, filename: str = "<unknown>") -> dict:
    """Regex-based parser for C / C++ files."""
    result = {"imports": [], "classes": {}, "functions": {}, "raw_code": code}

    for m in re.finditer(r'#include\s*[<"](.+?)[>"]', code):
        result["imports"].append(m.group(1))

    for m in re.finditer(r'class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?\s*\{', code):
        cls_name = m.group(1)
        bases = [m.group(2)] if m.group(2) else []
        methods = {}
        class_start = m.end()
        for mm in re.finditer(r'(?:virtual\s+)?(?:static\s+)?(?:[\w:*&<>]+)\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?\{', code[class_start:]):
            mname = mm.group(1)
            if mname not in ("if", "for", "while", "switch"):
                methods[mname] = {
                    "calls": _extract_function_calls(code[class_start + mm.start():class_start + mm.end() + 300]),
                    "line_start": code[:class_start + mm.start()].count('\n') + 1,
                    "line_end": code[:class_start + mm.end()].count('\n') + 1,
                    "docstring": ""
                }
        result["classes"][cls_name] = {
            "bases": bases, "methods": methods,
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.end()].count('\n') + 1,
            "docstring": ""
        }

    for m in re.finditer(r'(?:typedef\s+)?struct\s+(\w+)\s*\{', code):
        sname = m.group(1)
        if sname not in result["classes"]:
            result["classes"][sname] = {
                "bases": [], "methods": {},
                "line_start": code[:m.start()].count('\n') + 1,
                "line_end": code[:m.end()].count('\n') + 1,
                "docstring": ""
            }

    for m in re.finditer(r'^(?:[\w:*&<>]+)\s+(\w+)\s*\([^)]*\)\s*\{', code, re.MULTILINE):
        fname = m.group(1)
        if fname not in ("if", "for", "while", "switch", "main") and fname not in result.get("classes", {}):
            body_snippet = code[m.start():m.start() + 500]
            result["functions"][fname] = {
                "calls": _extract_function_calls(body_snippet),
                "line_start": code[:m.start()].count('\n') + 1,
                "line_end": code[:m.start()].count('\n') + 5,
                "docstring": ""
            }
    for m in re.finditer(r'(?:int|void)\s+main\s*\([^)]*\)\s*\{', code):
        body_snippet = code[m.start():m.start() + 500]
        result["functions"]["main"] = {
            "calls": _extract_function_calls(body_snippet),
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.start()].count('\n') + 5,
            "docstring": ""
        }

    return result


def parse_go(code: str, filename: str = "<unknown>") -> dict:
    """Regex-based parser for Go files."""
    result = {"imports": [], "classes": {}, "functions": {}, "raw_code": code}

    for m in re.finditer(r'import\s+"([\w/.]+)"', code):
        result["imports"].append(m.group(1))
    for m in re.finditer(r'import\s*\((.*?)\)', code, re.DOTALL):
        for im in re.finditer(r'"([\w/.]+)"', m.group(1)):
            result["imports"].append(im.group(1))

    for m in re.finditer(r'type\s+(\w+)\s+struct\s*\{', code):
        result["classes"][m.group(1)] = {
            "bases": [], "methods": {},
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.end()].count('\n') + 1,
            "docstring": ""
        }

    for m in re.finditer(r'type\s+(\w+)\s+interface\s*\{', code):
        result["classes"][m.group(1)] = {
            "bases": [], "methods": {},
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.end()].count('\n') + 1,
            "docstring": ""
        }

    for m in re.finditer(r'func\s+(?:\(\s*\w+\s+\*?(\w+)\s*\)\s+)?(\w+)\s*\(', code):
        receiver = m.group(1)
        fname = m.group(2)
        body_snippet = code[m.start():m.start() + 500]
        calls = _extract_function_calls(body_snippet)
        if receiver and receiver in result["classes"]:
            result["classes"][receiver]["methods"][fname] = {
                "calls": calls,
                "line_start": code[:m.start()].count('\n') + 1,
                "line_end": code[:m.start()].count('\n') + 5,
                "docstring": ""
            }
        else:
            result["functions"][fname] = {
                "calls": calls,
                "line_start": code[:m.start()].count('\n') + 1,
                "line_end": code[:m.start()].count('\n') + 5,
                "docstring": ""
            }

    return result


def parse_ruby(code: str, filename: str = "<unknown>") -> dict:
    """Regex-based parser for Ruby files."""
    result = {"imports": [], "classes": {}, "functions": {}, "raw_code": code}

    for m in re.finditer(r'''require\s+['"](.+?)['"]''', code):
        result["imports"].append(m.group(1))
    for m in re.finditer(r'''require_relative\s+['"](.+?)['"]''', code):
        result["imports"].append(m.group(1))

    for m in re.finditer(r'class\s+(\w+)(?:\s*<\s*(\w+))?', code):
        cls_name = m.group(1)
        bases = [m.group(2)] if m.group(2) else []
        methods = {}
        class_start = m.end()
        for mm in re.finditer(r'def\s+(?:self\.)?(\w+[?!=]?)', code[class_start:]):
            mname = mm.group(1)
            methods[mname] = {
                "calls": _extract_function_calls(code[class_start + mm.start():class_start + mm.end() + 300]),
                "line_start": code[:class_start + mm.start()].count('\n') + 1,
                "line_end": code[:class_start + mm.end()].count('\n') + 1,
                "docstring": ""
            }
        result["classes"][cls_name] = {
            "bases": bases, "methods": methods,
            "line_start": code[:m.start()].count('\n') + 1,
            "line_end": code[:m.end()].count('\n') + 1,
            "docstring": ""
        }

    for m in re.finditer(r'^def\s+(\w+[?!=]?)', code, re.MULTILINE):
        fname = m.group(1)
        if fname not in result["functions"]:
            body_snippet = code[m.start():m.start() + 500]
            result["functions"][fname] = {
                "calls": _extract_function_calls(body_snippet),
                "line_start": code[:m.start()].count('\n') + 1,
                "line_end": code[:m.start()].count('\n') + 5,
                "docstring": ""
            }

    return result


# ===================================================================
#  UNIVERSAL DISPATCHER
# ===================================================================

def parse_any_file(file_path: str) -> dict:
    """
    Dispatches to the correct parser based on file extension.
    Returns the standard { imports, classes, functions, raw_code } dict
    or { "error": "..." } on failure.
    """
    if not os.path.exists(file_path):
        return {"error": f"File does not exist: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()

    if ext in PYTHON_EXTENSIONS:
        return parse_file(file_path)
    elif ext in NOTEBOOK_EXTENSION:
        return parse_ipynb_file(file_path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
    except Exception as e:
        return {"error": f"Reading file failed: {str(e)}", "raw_code": ""}

    fname = os.path.basename(file_path)

    if ext in JS_EXTENSIONS:
        return parse_js_ts(code, fname)
    elif ext in JAVA_EXTENSIONS:
        return parse_java(code, fname)
    elif ext in C_EXTENSIONS:
        return parse_c_cpp(code, fname)
    elif ext in GO_EXTENSIONS:
        return parse_go(code, fname)
    elif ext in RUBY_EXTENSIONS:
        return parse_ruby(code, fname)
    else:
        # Fallback parser for text and configs (PHP, C#, SQL, shell, HTML, CSS, configs)
        return {
            "imports": _extract_generic_imports(code, ext),
            "classes": {},
            "functions": {},
            "raw_code": code
        }
