import platform
import subprocess
import sys

def main():
    os_type = platform.system()
    if os_type == "Windows":
        print("📍 Détection de Windows...")
        result = subprocess.run(["cmd", "/c", "install_windows.bat"])
        if result.returncode != 0:
            print("❌ Une erreur est survenue lors de l'installation sur Windows.")
            sys.exit(result.returncode)
    elif os_type in ("Linux", "Darwin"):
        print("📍 Détection de Linux/MacOS...")
        result = subprocess.run(["bash", "install_unix.sh"])
        if result.returncode != 0:
            print("❌ Une erreur est survenue lors de l'installation sur Linux/MacOS.")
            sys.exit(result.returncode)
    else:
        print(f"❌ Système d'exploitation non supporté: {os_type}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Installation de YemTech Pro...")
    main()