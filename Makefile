.PHONY: current-main-run current-main-smoke current-main-test current-main-preflight v2-release-rehearsal v2-release-rehearsal-debug

PYTHON := python3
ifneq (,$(wildcard .venv/bin/python))
PYTHON := ./.venv/bin/python
endif

current-main-run:
	bash scripts/restart_current_main.sh

current-main-smoke:
	$(PYTHON) scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8787

current-main-test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

current-main-preflight: current-main-test current-main-smoke

v2-release-rehearsal:
	bash scripts/release_rehearsal.sh

v2-release-rehearsal-debug:
	@if [ -z "$(ALLOW_DIRTY_REASON)" ]; then \
		echo "缺少 ALLOW_DIRTY_REASON。示例: make v2-release-rehearsal-debug ALLOW_DIRTY_REASON='本地联调临时放宽'"; \
		exit 2; \
	fi
	bash scripts/release_rehearsal.sh --allow-dirty-reason "$(ALLOW_DIRTY_REASON)"
