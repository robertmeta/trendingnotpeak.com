PYTHON ?= python3
.PHONY: help build lint test verify serve test-journeys test-mobile-audio test-podcast test-reel-motion test-discovery
help:
	@echo 'make build | verify | serve PORT=8765'
build:
	$(PYTHON) tools/build.py
lint:
	$(PYTHON) -m compileall -q tools
test: build
	$(PYTHON) -m unittest discover -s tools -p 'test_*.py' -v
verify: lint test
test-journeys:
	node tools/browser-journey.cjs
test-mobile-audio:
	node tools/mobile-audio-journey.cjs
test-reel-motion:
	node tools/reel-motion-journey.cjs
test-podcast:
	node tools/podcast-journey.cjs
test-discovery:
	node tools/discovery-journey.cjs
serve: build
	@test -n "$(PORT)" || (echo 'Set PORT explicitly: make serve PORT=8765'; exit 1)
	$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1 --directory docs
