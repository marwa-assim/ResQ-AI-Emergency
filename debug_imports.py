import sys
print("Python path:", sys.executable)
try:
    import flask
    print("Flask ok")
except ImportError as e:
    print("Flask failed:", e)

try:
    import mindspore
    print("MindSpore ok")
except ImportError as e:
    print("MindSpore failed:", e)
