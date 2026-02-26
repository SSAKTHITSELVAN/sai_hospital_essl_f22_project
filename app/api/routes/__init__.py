# app/api/routes/__init__.py - SIMPLEST FIX
"""API route modules"""

# Import modules and expose them
from . import users
from . import attendance
from . import device
from . import iclock
from . import payroll
from . import auth
from . import lop

# Make sure they're accessible
__all__ = ['users', 'attendance', 'device', 'iclock', 'payroll', 'auth', 'lop']