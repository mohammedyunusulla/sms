Ready-made Linux packages (Python 3.11, x86_64 and ARM) for the Homework AI QR reader, installed by the
Dockerfile with `pip install --no-index` so the server build needs no internet for them (pypi.org was unreachable
from the dev server's containers on 2026-11-20). To change a version: update requirements-qr.txt and the Dockerfile,
then re-download with
  pip download --only-binary=:all: --no-deps --python-version 3.11 --implementation cp \
    --platform manylinux_2_28_x86_64 --platform manylinux_2_28_aarch64 --dest wheels zxing-cpp==X pillow==Y
