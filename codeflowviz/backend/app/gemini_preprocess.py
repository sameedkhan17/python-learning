import os
import ast
from typing import Any, Dict, Optional, Tuple

import httpx


GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    class DocstringStripper(ast.NodeTransformer):
        def visit_FunctionDef(self, node: ast.FunctionDef):
            self.generic_visit(node)
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
            return node

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.generic_visit(node)
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
            return node

        def visit_ClassDef(self, node: ast.ClassDef):
            self.generic_visit(node)
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
            return node

        def visit_Module(self, node: ast.Module):
            self.generic_visit(node)
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
            return node

    return DocstringStripper().visit(tree)


def _local_preprocess(code: str) -> str:
    # Parse, strip docstrings, and unparse to drop comments while preserving semantics
    tree = ast.parse(code)
    tree = _strip_docstrings(tree)
    cleaned = ast.unparse(tree)
    return cleaned.strip() + "\n"


async def _try_gemini_preprocess_async(code: str, timeout_sec: float = 8.0) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None
    system_prompt = (
        "You are a code preprocessor. Remove all comments and docstrings from the provided Python code. "
        "Return ONLY the cleaned Python code with no explanations, no markdown fences. Preserve semantics."
    )

    # REST call compatible with Generative Language API v1beta
    # If the model alias differs, the endpoint should still work with a valid model name.
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": system_prompt + "\n\n" + code}]}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.post(endpoint, headers=headers, params={"key": GEMINI_API_KEY}, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Extract text
            candidates = data.get("candidates") or []
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            if not text.strip():
                return None
            # Strip code fences if model returns them
            if text.strip().startswith("```"):
                # naive fence strip
                lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
                text = "\n".join(lines).strip()
            return text.strip() + "\n"
    except Exception:
        return None


def preprocess_code(code: str, prefer_gemini: bool = True) -> Tuple[str, Dict[str, Any]]:
    # Try Gemini first if requested and configured; fallback to local
    if prefer_gemini:
        try:
            import anyio
            gemini_clean = anyio.run(_try_gemini_preprocess_async, code)
        except Exception:
            gemini_clean = None
        if gemini_clean:
            return gemini_clean, {"engine": "gemini", "model": GEMINI_MODEL_NAME}

    # Local deterministic fallback
    try:
        cleaned = _local_preprocess(code)
        return cleaned, {"engine": "local-ast", "model": "python-ast-unparse"}
    except Exception as exc:
        # As a last resort, return original code
        return code, {"engine": "noop", "error": str(exc)}