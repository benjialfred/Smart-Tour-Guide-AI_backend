#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Auto-switch to .venv if running outside the virtual environment on Windows/Unix
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python_win = os.path.join(base_dir, '.venv', 'Scripts', 'python.exe')
    venv_python_nix = os.path.join(base_dir, '.venv', 'bin', 'python')

    # If running with global Python and .venv exists, seamlessly re-run inside .venv
    if sys.prefix == sys.base_prefix:
        target_python = venv_python_win if os.path.exists(venv_python_win) else (venv_python_nix if os.path.exists(venv_python_nix) else None)
        if target_python and os.path.abspath(sys.executable) != os.path.abspath(target_python):
            import subprocess
            result = subprocess.run([target_python] + sys.argv)
            sys.exit(result.returncode)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_guide_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
