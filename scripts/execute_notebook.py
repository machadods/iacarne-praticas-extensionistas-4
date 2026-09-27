"""Executa a EDA integral usando o mesmo Python que iniciou este comando."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "notebooks/01_eda_inicial.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    # Kernel temporário garante uso do venv sem alterar kernels do usuário.
    with TemporaryDirectory() as tmp:
        import json
        kernel = Path(tmp) / "iacarne"
        kernel.mkdir()
        (kernel / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "iaCarne", "language": "python",
        }), encoding="utf-8")
        manager = KernelSpecManager(kernel_dirs=[tmp])
        from jupyter_client import KernelManager
        km = KernelManager(kernel_name="iacarne", kernel_spec_manager=manager)
        client = NotebookClient(notebook, km=km, timeout=180, resources={"metadata": {"path": str(root)}})
        try:
            client.execute()
        finally:
            if km.has_kernel:
                km.shutdown_kernel(now=True)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    print(f"Notebook executado e salvo: {path}")


if __name__ == "__main__":
    main()
