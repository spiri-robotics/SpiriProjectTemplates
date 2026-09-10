"""Generate a project from the template and build its documentation."""

import shutil
import subprocess
import sys
from pathlib import Path

# Use copier (available as a system tool)
try:
    import copier
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "copier"], check=False)
    import copier

TEMPLATE_DIR = Path(__file__).resolve().parent.parent
PROJECT_NAME = "demo-doc"
OUTPUT_DIR = Path("/tmp/spiri-demo")
PROJECT_DIR = None


def generate_project():
    """Generate a project with docs enabled."""
    global PROJECT_DIR
    print("Generating project from template...")
    copier.run_copy(
        str(TEMPLATE_DIR),
        OUTPUT_DIR,
        data={
            "project_name": PROJECT_NAME,
            "python_package_name": "demo_doc",
            "description": "Demo project with documentation",
            "version": "0.1.0",
            "author_name": "Demo User",
            "author_email": "demo@example.com",
            "license": "MIT",
            "spiri_config_plugin": False,
            "include_tests": True,
            "include_docs": True,
            "include_nix": False,
        },
        unsafe=True,
        defaults=True,
        overwrite=True,
        cleanup_on_error=False,
        quiet=True,
    )
    PROJECT_DIR = OUTPUT_DIR / PROJECT_NAME
    print(f"✓ Generated project at {PROJECT_DIR}")


def install_project(project_dir):
    """Install the generated project's dependencies."""
    print(f"\nInstalling dependencies for {project_dir}...")
    subprocess.run(["uv", "sync"], cwd=project_dir, check=True)
    subprocess.run(["uv", "pip", "install", "sphinx>=9.0", "furo>=2024.0", "myst-parser>=5.0"], cwd=project_dir, check=True)
    print("✓ Dependencies installed")


def build_docs(project_dir):
    """Build Sphinx documentation for the generated project."""
    docs_dir = project_dir / "docs"
    build_dir = docs_dir / "_build"
    
    print("\nBuilding docs with sphinx-build...")
    subprocess.run(
        ["sphinx-build", "-b", "html", str(docs_dir), str(build_dir)],
        cwd=project_dir,
        check=True,
    )
    
    return build_dir


def main():
    """Run the full pipeline."""
    import shutil
    
    # Clean up from previous runs
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    
    generate_project()
    
    print("\n" + "=" * 60)
    print("Installed project structure:")
    print("=" * 60)
    for item in list(PROJECT_DIR.rglob("*")):
        if item.is_file() and PROJECT_DIR:
            rel = item.relative_to(PROJECT_DIR)
            print(f"  {rel}")
    
    # Install dependencies
    try:
        if not PROJECT_DIR:
            print("⚠ Project directory not set!")
            return
        install_project(PROJECT_DIR)
    except subprocess.CalledProcessError as e:
        print(f"⚠ Dependency installation failed (skipping docs build): {e}")
        return
    
    # Build docs
    try:
        if not PROJECT_DIR:
            print("⚠ Project directory not set!")
            return
        build_docs_dir = build_docs(PROJECT_DIR)
        
        print("\n" + "=" * 60)
        print("Generated documentation:")
        print("=" * 60)
        if build_docs_dir.exists():
            for html_file in build_docs_dir.rglob("*.html"):
                rel = html_file.relative_to(build_docs_dir)
                print(f"  docs/_build/{rel}")
            
            print(f"\nDocumentation HTML is at: {build_docs_dir}")
            print(f"Open with: python -m http.server 8888 --directory {build_docs_dir}")
        else:
            print(f"Documentation build directory not found at {build_docs_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Documentation build failed: {e}")


if __name__ == "__main__":
    main()
