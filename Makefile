PYTHON ?= python3
RUFF ?= ruff
PYTEST ?= pytest

.PHONY: lint test compile smoke verify

lint:
	$(RUFF) check .

test:
	$(PYTEST)

compile:
	$(PYTHON) -m compileall API

smoke:
	$(PYTHON) -m mdeasm_cli --help >/dev/null
	$(PYTHON) -m mdeasm_cli --version >/dev/null
	$(PYTHON) -m mdeasm_cli assets --help >/dev/null
	$(PYTHON) -m mdeasm_cli tasks --help >/dev/null
	$(PYTHON) -m mdeasm_cli doctor --help >/dev/null

verify: lint test compile smoke
