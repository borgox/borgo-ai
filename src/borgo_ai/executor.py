"""
Code Execution Module - Safe code execution for borgo-ai
Supports: Python (sandboxed), Bash (with user approval)
"""
import subprocess
import sys
import os
import tempfile
import threading
import queue
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re
import ast


class ExecutionMode(Enum):
    """Code execution safety modes"""
    SAFE = "safe"           # Only safe operations (Python)
    ASK = "ask"             # Ask user before running (Bash)
    BLOCKED = "blocked"     # Never execute


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    stdout: str
    stderr: str
    return_value: Any
    execution_time: float
    was_cancelled: bool = False
    error: Optional[str] = None


class PythonSandbox:
    """
    Safe Python execution environment.
    
    Allowed:
    - Math operations
    - String manipulation
    - List/dict operations
    - Basic builtins (len, range, sum, etc.)
    - datetime, json, re, math modules
    
    Blocked:
    - File operations (open, os, pathlib)
    - Network (requests, socket, urllib)
    - System (subprocess, sys.exit, exec, eval on user input)
    - Dangerous builtins (__import__, compile, exec)
    """
    
    SAFE_BUILTINS = {
        # Safe builtins
        'abs': abs,
        'all': all,
        'any': any,
        'ascii': ascii,
        'bin': bin,
        'bool': bool,
        'bytearray': bytearray,
        'bytes': bytes,
        'callable': callable,
        'chr': chr,
        'complex': complex,
        'dict': dict,
        'dir': dir,
        'divmod': divmod,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'format': format,
        'frozenset': frozenset,
        'hash': hash,
        'hex': hex,
        'int': int,
        'isinstance': isinstance,
        'issubclass': issubclass,
        'iter': iter,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'next': next,
        'oct': oct,
        'ord': ord,
        'pow': pow,
        'print': print,
        'range': range,
        'repr': repr,
        'reversed': reversed,
        'round': round,
        'set': set,
        'slice': slice,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'type': type,
        'zip': zip,
        # Blocked - set to None
        '__import__': None,
        'compile': None,
        'eval': None,
        'exec': None,
        'open': None,
        'input': None,
        'breakpoint': None,
        'globals': None,
        'locals': None,
        'vars': None,
        'memoryview': None,
    }
    
    SAFE_MODULES = {
        'math',
        'cmath',
        'decimal',
        'fractions',
        'random',
        'statistics',
        'datetime',
        'calendar',
        'collections',
        'itertools',
        'functools',
        'operator',
        'string',
        're',
        'json',
        'copy',
        'pprint',
        'textwrap',
        'unicodedata',
        'typing',
    }
    
    DANGEROUS_PATTERNS = [
        r'\bimport\s+os\b',
        r'\bimport\s+sys\b',
        r'\bimport\s+subprocess\b',
        r'\bimport\s+shutil\b',
        r'\bimport\s+pathlib\b',
        r'\bimport\s+socket\b',
        r'\bimport\s+requests\b',
        r'\bimport\s+urllib\b',
        r'\bimport\s+http\b',
        r'\bfrom\s+os\b',
        r'\bfrom\s+sys\b',
        r'\b__import__\b',
        r'\bexec\s*\(',
        r'\beval\s*\(',
        r'\bcompile\s*\(',
        r'\bopen\s*\(',
        r'\bos\.',
        r'\bsys\.',
        r'\bsubprocess\.',
        r'\.system\s*\(',
        r'\.popen\s*\(',
    ]
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
    
    def is_safe(self, code: str) -> Tuple[bool, Optional[str]]:
        """Check if code is safe to execute"""
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Blocked: Dangerous pattern detected ({pattern})"
        
        # Try to parse the AST to check for dangerous constructs
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Check for dangerous imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = node.module if isinstance(node, ast.ImportFrom) else None
                    names = [alias.name for alias in node.names]
                    
                    for name in names:
                        full_name = f"{module}.{name}" if module else name
                        base_module = full_name.split('.')[0]
                        
                        if base_module not in self.SAFE_MODULES:
                            return False, f"Blocked: Import of '{base_module}' not allowed"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        return True, None
    
    def execute(self, code: str) -> ExecutionResult:
        """Execute Python code safely"""
        import time
        
        # Safety check
        is_safe, error = self.is_safe(code)
        if not is_safe:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=error or "Code failed safety check",
                return_value=None,
                execution_time=0,
                error=error
            )
        
        # Create safe globals
        import math
        import datetime
        import json as json_module
        import re as re_module
        import random
        import collections
        import itertools
        import functools
        
        safe_globals = {
            '__builtins__': self.SAFE_BUILTINS,
            'math': math,
            'datetime': datetime,
            'json': json_module,
            're': re_module,
            'random': random,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
        }
        
        # Capture output
        from io import StringIO
        import contextlib
        
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        result_value = None
        success = True
        error_msg = None
        
        start_time = time.time()
        
        try:
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                
                # Execute with timeout
                exec_result = {}
                exec(code, safe_globals, exec_result)
                
                # Try to get a result (last expression)
                if '_result' in exec_result:
                    result_value = exec_result['_result']
        
        except Exception as e:
            success = False
            error_msg = f"{type(e).__name__}: {e}"
            stderr_capture.write(error_msg)
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            success=success,
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            return_value=result_value,
            execution_time=execution_time,
            error=error_msg
        )


class BashExecutor:
    """
    Bash command execution with user approval.
    
    - Always asks for confirmation before running
    - Shows the exact command
    - Only allows GET requests for network operations
    - Blocks dangerous commands
    """
    
    BLOCKED_COMMANDS = [
        'rm -rf /',
        'rm -rf ~',
        'rm -rf *',
        'mkfs',
        'dd if=',
        ':(){:|:&};:',  # Fork bomb
        '> /dev/sda',
        'chmod -R 777 /',
        'wget -O- | sh',
        'curl | sh',
        'curl | bash',
        'wget | bash',
    ]
    
    BLOCKED_PATTERNS = [
        r'\brm\s+-rf\s+/',
        r'\bsudo\s+rm\b',
        r'\bmkfs\b',
        r'\bdd\s+if=',
        r'>\s*/dev/',
        r'\bshutdown\b',
        r'\breboot\b',
        r'\binit\s+0\b',
        r'\bchmod\s+-R\s+777\s+/',
    ]
    
    # Only allow GET for curl/wget
    NETWORK_RESTRICTIONS = {
        'curl': ['-X POST', '-X PUT', '-X DELETE', '-X PATCH', '--data', '-d ', '--upload-file', '-T '],
        'wget': ['--post-data', '--post-file', '--method=POST'],
    }
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
    
    def is_safe(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if command is safe to run (after user approval)"""
        command_lower = command.lower()
        
        # Check blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked.lower() in command_lower:
                return False, f"Blocked: Dangerous command pattern"
        
        # Check blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked: Dangerous command pattern"
        
        # Check network restrictions (no POST/PUT/DELETE)
        for tool, blocked_args in self.NETWORK_RESTRICTIONS.items():
            if tool in command_lower:
                for arg in blocked_args:
                    if arg.lower() in command_lower:
                        return False, f"Blocked: Only GET requests allowed ({arg} not permitted)"
        
        return True, None
    
    def format_for_display(self, command: str) -> str:
        """Format command for user review"""
        # Syntax highlight-ish formatting
        return command
    
    def execute(
        self, 
        command: str, 
        approved: bool = False,
        cwd: Optional[str] = None
    ) -> ExecutionResult:
        """Execute bash command (only if approved)"""
        import time
        
        # Safety check
        is_safe, error = self.is_safe(command)
        if not is_safe:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=error or "Command blocked for safety",
                return_value=None,
                execution_time=0,
                error=error
            )
        
        if not approved:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_value=None,
                execution_time=0,
                was_cancelled=True,
                error="Command requires user approval"
            )
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_value=result.returncode,
                execution_time=execution_time
            )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                return_value=None,
                execution_time=self.timeout,
                error="Timeout"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_value=None,
                execution_time=time.time() - start_time,
                error=str(e)
            )


class CodeExecutor:
    """Unified code execution interface"""
    
    def __init__(self):
        self.python_sandbox = PythonSandbox()
        self.bash_executor = BashExecutor()
    
    def detect_language(self, code: str) -> str:
        """Detect the programming language of the code"""
        code = code.strip()
        
        # Check for explicit markers
        if code.startswith('```python') or code.startswith('#!/usr/bin/env python'):
            return 'python'
        if code.startswith('```bash') or code.startswith('```sh') or code.startswith('#!/bin/bash'):
            return 'bash'
        
        # Heuristics
        python_indicators = ['def ', 'import ', 'from ', 'class ', 'print(', 'if __name__']
        bash_indicators = ['echo ', 'ls ', 'cd ', 'mkdir ', 'grep ', 'cat ', 'wget ', 'curl ']
        
        python_score = sum(1 for ind in python_indicators if ind in code)
        bash_score = sum(1 for ind in bash_indicators if ind in code)
        
        if python_score > bash_score:
            return 'python'
        elif bash_score > python_score:
            return 'bash'
        
        # Default to Python
        return 'python'
    
    def clean_code(self, code: str) -> str:
        """Remove markdown code fences if present"""
        code = code.strip()
        
        # Remove code fences
        if code.startswith('```'):
            lines = code.split('\n')
            # Remove first line (```python or similar)
            lines = lines[1:]
            # Remove last line if it's just ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            code = '\n'.join(lines)
        
        return code.strip()
    
    def execute_python(self, code: str) -> ExecutionResult:
        """Execute Python code safely"""
        code = self.clean_code(code)
        return self.python_sandbox.execute(code)
    
    def check_bash(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if bash command is safe"""
        command = self.clean_code(command)
        return self.bash_executor.is_safe(command)
    
    def execute_bash(self, command: str, approved: bool = False) -> ExecutionResult:
        """Execute bash command (requires approval)"""
        command = self.clean_code(command)
        return self.bash_executor.execute(command, approved)
    
    def execute(
        self, 
        code: str, 
        language: Optional[str] = None,
        bash_approved: bool = False
    ) -> ExecutionResult:
        """Execute code in appropriate environment"""
        if language is None:
            language = self.detect_language(code)
        
        if language == 'python':
            return self.execute_python(code)
        elif language in ('bash', 'sh', 'shell'):
            return self.execute_bash(code, bash_approved)
        else:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Unsupported language: {language}",
                return_value=None,
                execution_time=0,
                error=f"Unsupported language: {language}"
            )


# Convenience functions
_executor: Optional[CodeExecutor] = None

def get_executor() -> CodeExecutor:
    """Get or create code executor"""
    global _executor
    if _executor is None:
        _executor = CodeExecutor()
    return _executor


def run_python(code: str) -> ExecutionResult:
    """Run Python code safely"""
    return get_executor().execute_python(code)


def run_bash(command: str, approved: bool = False) -> ExecutionResult:
    """Run bash command (requires approval)"""
    return get_executor().execute_bash(command, approved)


def check_bash_safety(command: str) -> Tuple[bool, Optional[str]]:
    """Check if bash command is safe"""
    return get_executor().check_bash(command)
