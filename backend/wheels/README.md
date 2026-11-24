Ready-made Linux packages (Python 3.11, x86_64 and ARM) for the Homework AI QR reader, installed by the
Dockerfile with `pip install --no-index` so the server build needs no internet for them (pypi.org was unreachable
from the dev server's containers on 2026-11-20). To change a version: update requirements-qr.txt and the Dockerfile,
then re-download with
  pip download --only-binary=:all: --no-deps --python-version 3.11 --implementation cp \
    --platform manylinux_2_28_x86_64 --platform manylinux_2_28_aarch64 --dest wheels zxing-cpp==X pillow==Y

Push notifications (requirements-push.txt): pywebpush, py-vapid, http-ece - pure Python (py3-none-any), so one
file each works on every server. Their own needs (cryptography, requests, six) come from requirements.txt.
To change a version: update requirements-push.txt and the Dockerfile, then
  pip download --only-binary=:all: --no-deps --dest wheels pywebpush==X py-vapid==Y
  pip wheel --no-deps -w wheels http-ece==Z        (only published as source, so build the wheel)

Never add new packages to requirements.txt: any change there makes the server re-download every package from
pypi.org, which it can't reach, and the deploy fails (happened 2026-11-24). Bundle them here instead.
