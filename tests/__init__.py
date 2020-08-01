import subprocess
import sys

subprocess.check_call(
    ["git", "config", "--local", "user.email", "you@example.com"]
)
subprocess.check_call(["git", "config", "--local", "user.name", "Your Name"])


sys.path.insert(0, "../")
