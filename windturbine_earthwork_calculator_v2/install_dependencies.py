"""
Dependency installer for Wind Turbine Earthwork Calculator V2

This script checks and installs required Python packages that are not
included in the standard QGIS installation.

Author: Wind Energy Site Planning
Version: 2.0.0
"""

import sys
import subprocess
import os
from pathlib import Path


def check_import(package_name, import_name=None):
    """
    Check if a package can be imported.

    Args:
        package_name (str): Name of the package (for pip install)
        import_name (str): Name to use for import (if different from package_name)

    Returns:
        bool: True if package is available, False otherwise
    """
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def install_package(package_name, version=None):
    """
    Install a Python package using pip.

    Args:
        package_name (str): Name of the package to install
        version (str): Optional version specifier (e.g., ">=1.1.0")

    Returns:
        bool: True if installation successful, False otherwise
    """
    if version:
        package_spec = f"{package_name}{version}"
    else:
        package_spec = package_name

    print(f"Installing {package_spec}...")

    try:
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--user",
            package_spec
        ])
        print(f"✓ Successfully installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package_name}: {e}")
        return False


def get_environment_info():
    """
    Get diagnostic information about the Python environment.

    Returns:
        dict: Environment information
    """
    info = {
        'python_version': sys.version,
        'python_executable': sys.executable,
        'platform': sys.platform,
        'site_packages': [p for p in sys.path if 'site-packages' in p.lower()],
    }
    return info


def print_environment_info():
    """Print environment information for debugging."""
    info = get_environment_info()
    print("\n" + "=" * 60)
    print("Python Environment Information")
    print("=" * 60)
    print(f"Python version: {info['python_version'].split()[0]}")
    print(f"Executable: {info['python_executable']}")
    print(f"Platform: {info['platform']}")
    print("\nSite-packages paths:")
    for path in info['site_packages'][:5]:
        print(f"  - {path}")
    print("")


def install_dependencies():
    """
    Check and install all required dependencies.

    Returns:
        tuple: (success: bool, missing_packages: list)
    """
    dependencies = {
        'ezdxf': ('ezdxf', '>=1.1.0'),
        'shapely': ('shapely', '>=2.0.0'),
        'requests': ('requests', '>=2.28.0'),
    }

    missing = []
    installed = []
    failed = []

    print("=" * 60)
    print("Wind Turbine Earthwork Calculator V2 - Dependency Check")
    print("=" * 60)

    # Check which packages are missing
    for import_name, (package_name, version) in dependencies.items():
        if check_import(import_name):
            print(f"✓ {package_name} is already installed")
            installed.append(package_name)
        else:
            print(f"✗ {package_name} is not installed")
            missing.append((package_name, version))

    # Install missing packages
    if missing:
        print("\n" + "=" * 60)
        print("Installing missing packages...")
        print("=" * 60 + "\n")

        for package_name, version in missing:
            if install_package(package_name, version):
                installed.append(package_name)
            else:
                failed.append(package_name)

    # Summary
    print("\n" + "=" * 60)
    print("Installation Summary")
    print("=" * 60)
    print(f"Already installed: {len(installed) - len(missing)}")
    print(f"Newly installed: {len(missing) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\n⚠ WARNING: The following packages could not be installed:")
        for pkg in failed:
            print(f"  - {pkg}")
        print("\nPlease install them manually using:")
        print(f"  pip install --user {' '.join(failed)}")
        return False, failed

    print("\n✓ All dependencies are installed successfully!")
    return True, []


def main():
    """Main entry point for the dependency installer."""
    # Print environment information for debugging
    print_environment_info()

    success, missing = install_dependencies()

    if not success:
        print("\n" + "=" * 60)
        print("⚠ INSTALLATION INCOMPLETE")
        print("=" * 60)
        print("The plugin may not work correctly without all dependencies.")
        print("Please resolve the installation issues before using the plugin.")
        print("\nFor QGIS on Windows, try using the OSGeo4W Shell:")
        print("  1. Open OSGeo4W Shell (Start Menu -> OSGeo4W -> OSGeo4W Shell)")
        print("  2. Run: pip install ezdxf shapely")
        sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("✓ INSTALLATION COMPLETE")
        print("=" * 60)
        print("You can now use the Wind Turbine Earthwork Calculator V2 plugin.")
        print("Find it in: Processing Toolbox → Wind Turbine → Optimize Platform Height")


if __name__ == "__main__":
    main()
