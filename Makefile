VERSION ?= 7.6.1
GAME_DIR ?=
GAME_ID ?=
ENGINE_NRO ?= dist/$(VERSION)/renounce-renpy-$(VERSION).nro

.PHONY: engine game editable-nro

# Each target creates its own output; none patches a shared input in place.
engine:
	bash build-engine.bash $(VERSION)

game:
	@test -n "$(GAME_DIR)" || { echo 'Set GAME_DIR=/path/to/project' >&2; exit 2; }
	@if [ "$(VERSION)" = 8.4.1 ]; then \
		test -n "$(GAME_ID)" || { echo 'Set GAME_ID for RenPy 8.4.1' >&2; exit 2; }; \
		python3 build-game-from-base.py "$(GAME_DIR)" --base "packager/renounce-base-8.4.1.nro" --id "$(GAME_ID)"; \
	else \
		bash build-game.bash "$(GAME_DIR)" $(if $(GAME_ID),--id "$(GAME_ID)",); \
	fi

editable-nro:
	python3 build-editable-nro.py "$(ENGINE_NRO)" --version "$(VERSION)"
