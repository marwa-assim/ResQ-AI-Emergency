import sys
import os
print("Python Executable:", sys.executable)
print("System Path:")
for p in sys.path:
    print(p)

try:
    import flask_sqlalchemy
    print("Flask-SQLAlchemy found at:", flask_sqlalchemy.__file__)
except ImportError as e:
    print("ImportError:", e)
