PYTHON ?= python3

.PHONY: validate test serve-api tree

validate:
	$(PYTHON) scripts/validate_scaffold.py

test:
	$(PYTHON) -m unittest discover -s tests -t .

serve-api:
	$(PYTHON) -m apps.api.main

tree:
	$(PYTHON) scripts/validate_scaffold.py --tree
