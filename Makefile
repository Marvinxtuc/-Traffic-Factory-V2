.PHONY: v1-check-ui-language v1-runtime-smoke v1-preflight

PYTHON := python3
ifneq (,$(wildcard .venv/bin/python))
PYTHON := ./.venv/bin/python
endif

v1-check-ui-language:
	$(PYTHON) scripts/check_ui_language.py

v1-runtime-smoke:
	$(PYTHON) scripts/runtime_smoke_test.py --base-url http://127.0.0.1:8788 --cleanup

v1-preflight: v1-check-ui-language v1-runtime-smoke
