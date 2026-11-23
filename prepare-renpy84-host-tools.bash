#!/usr/bin/env bash
# Build isolated Python 3.12 host tooling for Ren'Py's Cython generator.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
PYTHON="$ROOT/build-python312/host/python"
WORK="$ROOT/build-renpy8/host-tools"
WHEELS="$WORK/wheels"
mkdir -p "$WHEELS" "$WORK/bin"
fetch() {
    local url=$1 file=$2 digest=$3
    if [ ! -f "$WHEELS/$file" ]; then
        curl -fsSL "$url" -o "$WHEELS/$file"
    fi
    printf '%s  %s\n' "$digest" "$WHEELS/$file" | sha256sum -c -
}
fetch 'https://files.pythonhosted.org/packages/69/8a/b9dc7678803429e4a3bc9ba462fa3dd9066824d3c607490235c6a796be5a/setuptools-75.8.0-py3-none-any.whl' \
    setuptools-75.8.0-py3-none-any.whl e3982f444617239225d675215d51f6ba05f845d4eec313da4418fdbb56fb27e3
fetch 'https://files.pythonhosted.org/packages/9a/ef/44af6aded89444dc45f4466ff207a05d3376c641cf1146c03fd14c55ae64/Cython-3.0.11-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl' \
    Cython-3.0.11-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl 8b14c24f1dc4c4c9d997cca8d1b7fb01187a218aab932328247dcf5694a10102
if [ ! -d "$WORK/site/Cython" ]; then
    PIP_WHEEL=$(find "$ROOT/build-python312/Python-3.12.8/Lib/ensurepip/_bundled" -name 'pip-*.whl' -print -quit)
    PYTHONPATH="$PIP_WHEEL" "$PYTHON" -m pip install --no-index \
        --find-links "$WHEELS" --target "$WORK/site" \
        setuptools==75.8.0 Cython==3.0.11
fi
cat > "$WORK/bin/python3" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$WORK/site\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$PYTHON" "\$@"
EOF
cat > "$WORK/bin/cython" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$WORK/site\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$PYTHON" -m cython "\$@"
EOF
chmod +x "$WORK/bin/python3" "$WORK/bin/cython"
