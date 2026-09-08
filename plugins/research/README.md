# Research plugin runtime

The repository README owns plugin installation. This package contains the
AI Paper Search Python CLI and the five independent skills.

## Search environment

From this package directory, create the dedicated environment once:

```bash
conda env create -f environment.yml
```

Install or refresh the CLI from the current plugin package directory after
updates (including when its installed version directory changes):

```bash
conda run -n ai-paper-search python -m pip install .
conda run -n ai-paper-search ai-paper-search --help
conda run -n ai-paper-search ai-paper-bibtex --help
```

For source development use `python -m pip install -e '.[test]'` inside the same
Conda environment. A non-editable installation is preferable for usage because
plugin updates can remove old cache directories. Do not create a second copy
of a project's ML environment for this tool.

The arXiv MCP connection is declared in .mcp.json and uses the separately
installed `uvx` tool runtime. Search and arXiv do not depend on other plugins.
