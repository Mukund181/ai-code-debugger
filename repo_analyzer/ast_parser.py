import ast
import os

def parse_code(code_content: str, filename: str = "<unknown>") -> dict:
    """Parses python code using AST to find defined classes, functions, calls and imports."""
    try:
        tree = ast.parse(code_content, filename=filename)
    except Exception as e:
        return {"error": f"Syntax or Parse Error: {str(e)}"}

    result = {
        "imports": [],
        "classes": {},
        "functions": {},
        "raw_code": code_content
    }

    # Helper function to extract call names from AST nodes
    def extract_calls(node):
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # For self.foo() or module.foo()
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

    # Traverse top-level nodes
    for node in tree.body:
        # Imports
        if isinstance(node, ast.Import):
            for name in node.names:
                result["imports"].append(name.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for name in node.names:
                result["imports"].append(f"{module}.{name.name}" if module else name.name)

        # Classes
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

            # Inspect methods inside the class
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    method_name = child.name
                    class_info["methods"][method_name] = {
                        "calls": extract_calls(child),
                        "line_start": child.lineno,
                        "line_end": getattr(child, "end_lineno", child.lineno),
                        "docstring": ast.get_docstring(child) or ""
                    }
            result["classes"][class_name] = class_info

        # Top-level Functions
        elif isinstance(node, ast.FunctionDef):
            func_name = node.name
            result["functions"][func_name] = {
                "calls": extract_calls(node),
                "line_start": node.lineno,
                "line_end": getattr(node, "end_lineno", node.lineno),
                "docstring": ast.get_docstring(node) or ""
            }

    return result

def parse_file(file_path: str) -> dict:
    """Reads a local python file and parses its AST structure."""
    if not os.path.exists(file_path):
        return {"error": f"File does not exist: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return parse_code(content, filename=os.path.basename(file_path))
    except Exception as e:
        return {"error": f"Reading file failed: {str(e)}"}
