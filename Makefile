PYTHON ?= python3
RUFF ?= ruff
PYTEST ?= pytest

.PHONY: lint test compile smoke docs-smoke verify

lint:
	$(RUFF) check .

test:
	$(PYTEST)

compile:
	$(PYTHON) -m compileall API

smoke:
	$(PYTHON) -m mdeasm_cli --help >/dev/null
	$(PYTHON) -m mdeasm_cli --version >/dev/null
	$(PYTHON) -m mdeasm_cli completions bash --help >/dev/null
	$(PYTHON) -m mdeasm_cli assets --help >/dev/null
	$(PYTHON) -m mdeasm_cli tasks --help >/dev/null
	$(PYTHON) -m mdeasm_cli discovery-groups --help >/dev/null
	$(PYTHON) -m mdeasm_cli doctor --help >/dev/null

docs-smoke:
	$(PYTHON) -m mdeasm_cli assets export --help >/dev/null
	$(PYTHON) -m mdeasm_cli assets schema diff --help >/dev/null
	$(PYTHON) -m mdeasm_cli tasks wait --help >/dev/null
	$(PYTHON) -m mdeasm_cli tasks fetch --help >/dev/null
	$(PYTHON) -m mdeasm_cli discovery-groups list --help >/dev/null
	$(PYTHON) -m mdeasm_cli discovery-groups delete --help >/dev/null
	$(PYTHON) -m mdeasm_cli data-connections validate --help >/dev/null
	$(PYTHON) -m mdeasm_cli saved-filters put --help >/dev/null
	$(PYTHON) -m mdeasm_cli workspaces delete --help >/dev/null
	$(PYTHON) -m mdeasm_cli resource-tags put --help >/dev/null
	$(PYTHON) -m mdeasm_cli completions bash --out /tmp/mdeasm-docs-smoke-completion.bash
	$(PYTHON) -m mdeasm_cli completions zsh --out /tmp/mdeasm-docs-smoke-completion.zsh
	$(PYTHON) -c "import pathlib; data=pathlib.Path('/tmp/mdeasm-docs-smoke-completion.bash').read_text(encoding='utf-8'); assert '_mdeasm_complete' in data and 'complete -o default -F _mdeasm_complete mdeasm' in data"
	$(PYTHON) -c "import pathlib; data=pathlib.Path('/tmp/mdeasm-docs-smoke-completion.zsh').read_text(encoding='utf-8'); assert '#compdef mdeasm' in data and 'bashcompinit' in data"
	$(PYTHON) -m mdeasm_cli doctor --format json --out - >/tmp/mdeasm-docs-smoke-doctor.json || true
	$(PYTHON) -c "import json, pathlib; json.loads(pathlib.Path('/tmp/mdeasm-docs-smoke-doctor.json').read_text(encoding='utf-8'))"
	@if [ -n "$$TENANT_ID" ] && [ -n "$$SUBSCRIPTION_ID" ] && [ -n "$$CLIENT_ID" ] && [ -n "$$CLIENT_SECRET" ]; then \
		$(PYTHON) -m mdeasm_cli workspaces list --format json --out - >/tmp/mdeasm-docs-smoke-workspaces.json; \
		$(PYTHON) -c "import json, pathlib; payload=json.loads(pathlib.Path('/tmp/mdeasm-docs-smoke-workspaces.json').read_text(encoding='utf-8')); assert isinstance(payload, list), 'expected workspaces payload list'"; \
	else \
		echo "docs-smoke: skipping credentialed workspace smoke (missing required env vars)"; \
	fi

verify: lint test compile smoke docs-smoke
