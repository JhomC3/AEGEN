import subprocess
import sys


def run_gate(name: str, command: str) -> bool:
    print(f"Running gate: {name}...")
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Gate {name} passed.")
        return True
    except Exception:
        print(f"Gate {name} failed.")
        return False


def main() -> None:
    gates = {"lint": "make lint", "test": "make test"}
    success = True
    for name, cmd in gates.items():
        if not run_gate(name, cmd):
            success = False
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
