# Shell Completions (CLI)

Generate completion scripts directly from the current CLI parser:

```bash
source .venv/bin/activate
mdeasm completions bash
```

## Bash

One-time test in current shell:

```bash
source <(mdeasm completions bash)
```

Persist for future shells:

```bash
mkdir -p "${HOME}/.local/share/bash-completion/completions"
mdeasm completions bash --out "${HOME}/.local/share/bash-completion/completions/mdeasm"
```

## Zsh

One-time test in current shell:

```bash
source <(mdeasm completions zsh)
```

Persist by writing to a file sourced from `~/.zshrc`:

```bash
mkdir -p "${HOME}/.zsh/completions"
mdeasm completions zsh --out "${HOME}/.zsh/completions/_mdeasm"
echo 'fpath=("${HOME}/.zsh/completions" $fpath)' >> "${HOME}/.zshrc"
echo 'autoload -Uz compinit && compinit' >> "${HOME}/.zshrc"
echo 'source "${HOME}/.zsh/completions/_mdeasm"' >> "${HOME}/.zshrc"
```

Notes:
- Regenerate completions after upgrading to newer CLI commands/options.
- Completion suggestions include command paths and flags for each command scope.
