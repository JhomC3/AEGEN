# src/core/security/__init__.py
"""
Módulo de seguridad para MAGI.

Contiene componentes de autorización y control de acceso.
"""

from .access_controller import AccessController

__all__ = ["AccessController"]
