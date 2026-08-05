import subprocess


def main():
    subprocess.run(["ruff", "format", "."], check=True)
    subprocess.run(["ruff", "check", ".", "--fix"], check=True)
    subprocess.run(["ruff", "check", "."])


if __name__ == "__main__":
    main()
