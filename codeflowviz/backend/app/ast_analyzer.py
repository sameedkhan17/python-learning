import ast
import itertools
from typing import Any, Dict, List, Tuple


class CodeGraphBuilder(ast.NodeVisitor):
    def __init__(self) -> None:
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []
        self._node_seq = itertools.count(1)
        self._statement_seq = itertools.count(1)
        self.var_id_map: Dict[str, str] = {}
        self.current_function: List[str] = []

    def _next_node_id(self, prefix: str) -> str:
        return f"{prefix}{next(self._node_seq)}"

    def _ensure_var_node(self, var_name: str) -> str:
        if var_name not in self.var_id_map:
            node_id = self._next_node_id("v")
            self.var_id_map[var_name] = node_id
            self.nodes.append({"data": {"id": node_id, "label": var_name, "type": "var"}})
        return self.var_id_map[var_name]

    def _add_stmt_node(self, label: str, type_: str) -> str:
        stmt_id = f"s{next(self._statement_seq)}"
        self.nodes.append({"data": {"id": stmt_id, "label": label, "type": type_}})
        return stmt_id

    def _add_edge(self, source: str, target: str, label: str) -> None:
        edge_id = f"e{len(self.edges)+1}"
        self.edges.append({"data": {"id": edge_id, "source": source, "target": target, "label": label}})

    def _names_in(self, node: ast.AST) -> List[str]:
        names: List[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name):
                names.append(sub.id)
        return names

    def _handle_assign(self, node: ast.AST, targets: List[ast.expr], value: ast.AST, op_label: str = "assign"):
        label = op_label
        try:
            label_val = ast.unparse(value)
            label = f"{op_label}: {label_val}"
        except Exception:
            pass
        stmt_id = self._add_stmt_node(label, "assign")
        # Value uses
        for var in self._names_in(value):
            v_id = self._ensure_var_node(var)
            self._add_edge(v_id, stmt_id, "uses")
        # Targets defined
        for tgt in targets:
            if isinstance(tgt, ast.Name):
                v_id = self._ensure_var_node(tgt.id)
                self._add_edge(stmt_id, v_id, "defines")

    def visit_Assign(self, node: ast.Assign):
        self._handle_assign(node, node.targets, node.value, op_label="assign")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        targets = [node.target] if node.target else []
        value = node.value if node.value else ast.Name(id="<no value>")
        self._handle_assign(node, targets, value, op_label="annassign")
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        targets = [node.target]
        op = type(node.op).__name__
        self._handle_assign(node, targets, node.value, op_label=f"augassign {op}")
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            func_label = None
            try:
                func_label = ast.unparse(node.value.func)
            except Exception:
                func_label = "call"
            stmt_id = self._add_stmt_node(f"call: {func_label}", "call")
            # args uses
            for arg in node.value.args:
                for var in self._names_in(arg):
                    v_id = self._ensure_var_node(var)
                    self._add_edge(v_id, stmt_id, "arg")
            # keywords uses
            for kw in node.value.keywords:
                if kw.value is not None:
                    for var in self._names_in(kw.value):
                        v_id = self._ensure_var_node(var)
                        self._add_edge(v_id, stmt_id, kw.arg or "kw")
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        stmt_id = self._add_stmt_node("return", "return")
        if node.value is not None:
            for var in self._names_in(node.value):
                v_id = self._ensure_var_node(var)
                self._add_edge(v_id, stmt_id, "returns")
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        label = None
        try:
            label = ast.unparse(node.test)
        except Exception:
            label = "if"
        stmt_id = self._add_stmt_node(f"if: {label}", "if")
        for var in self._names_in(node.test):
            v_id = self._ensure_var_node(var)
            self._add_edge(v_id, stmt_id, "cond")
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        label = None
        try:
            label = ast.unparse(node.iter)
        except Exception:
            label = "for"
        stmt_id = self._add_stmt_node(f"for: {label}", "for")
        # data deps from iter
        for var in self._names_in(node.iter):
            v_id = self._ensure_var_node(var)
            self._add_edge(v_id, stmt_id, "iter")
        # defines loop targets
        if isinstance(node.target, ast.Name):
            v_id = self._ensure_var_node(node.target.id)
            self._add_edge(stmt_id, v_id, "defines")
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        label = None
        try:
            label = ast.unparse(node.test)
        except Exception:
            label = "while"
        stmt_id = self._add_stmt_node(f"while: {label}", "while")
        for var in self._names_in(node.test):
            v_id = self._ensure_var_node(var)
            self._add_edge(v_id, stmt_id, "cond")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        params = [arg.arg for arg in node.args.args]
        stmt_id = self._add_stmt_node(f"def {node.name}({', '.join(params)})", "function")
        # param var nodes
        for p in params:
            v_id = self._ensure_var_node(p)
            self._add_edge(stmt_id, v_id, "param")
        self.current_function.append(node.name)
        self.generic_visit(node)
        self.current_function.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        params = [arg.arg for arg in node.args.args]
        stmt_id = self._add_stmt_node(f"async def {node.name}({', '.join(params)})", "function")
        for p in params:
            v_id = self._ensure_var_node(p)
            self._add_edge(stmt_id, v_id, "param")
        self.current_function.append(node.name)
        self.generic_visit(node)
        self.current_function.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = []
        try:
            bases = [ast.unparse(b) for b in node.bases]
        except Exception:
            bases = []
        self._add_stmt_node(f"class {node.name}({', '.join(bases)})", "class")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        names = ", ".join(alias.name for alias in node.names)
        stmt_id = self._add_stmt_node(f"import {names}", "import")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        names = ", ".join(alias.name for alias in node.names)
        self._add_stmt_node(f"from {mod} import {names}", "import")
        self.generic_visit(node)


def analyze_python_code(code: str) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str], Dict[str, Any]]:
    diagnostics: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        diagnostics.append(f"SyntaxError: {e}")
        return {"nodes": [], "edges": []}, diagnostics, {"num_nodes": 0, "num_edges": 0}

    builder = CodeGraphBuilder()
    builder.visit(tree)

    graph = {"nodes": builder.nodes, "edges": builder.edges}
    stats = {"num_nodes": len(builder.nodes), "num_edges": len(builder.edges), "num_vars": len(builder.var_id_map)}
    return graph, diagnostics, stats