Public smoke tests for mini-posix-manifest-installer.

Each step_XX_smoke.py is an executable black-box smoke that inserts the codebase directory into sys.path before importing posix_manifest_installer. These smokes exercise only the disclosed public API and are expected to pass against the complete Oracle implementation.
