SHELL = /usr/bin/env bash -xeuo pipefail

create-quadlet:
	uv run scripts/create_quadlets.py

check-secret:
	podman secret exists cf_tunnel_token

register-secret:
	@set +x; \
	if [ -z "$${CF_TUNNEL_TOKEN:-}" ]; then \
		echo "Error: CF_TUNNEL_TOKEN is not set" >&2; \
		exit 1; \
	fi; \
	podman secret rm cf_tunnel_token 2>/dev/null || true; \
	printf '%s' "$$CF_TUNNEL_TOKEN" | podman secret create cf_tunnel_token -

deploy-quadlet: check-secret create-quadlet
	@for file in \
		kaleido-api-content.volume \
		kaleido-api-nginx.container \
		kaleido-api.network \
		kaleido-api-app.build \
		kaleido-api-app.container \
		kaleido-api-cloudflared.container; do \
		if [ ! -f "dist/quadlet/$$file" ]; then \
			echo "Error: $$file was not generated" >&2; \
			exit 1; \
		fi; \
	done
	mkdir -p "$$HOME/.config/containers/systemd"
	cp dist/quadlet/* "$$HOME/.config/containers/systemd/"
	systemctl --user daemon-reload
	@echo "start wait"
	sleep 10
	@echo "wait 10sec"
	sleep 10
	@echo "wait 20sec"
	sleep 10
	@echo "wait 30sec"
	sleep 10
	@echo "wait 40sec"
	sleep 10
	@echo "wait 50sec"
	sleep 10
	@echo "wait 60sec"
	@systemctl --user list-unit-files | grep -q '^kaleido-api-nginx\.service' || { \
		echo "Error: kaleido-api-nginx.service was not generated" >&2; \
		exit 1; \
	}
	@systemctl --user list-unit-files | grep -q '^kaleido-api-cloudflared\.service' || { \
		echo "Error: kaleido-api-cloudflared.service was not generated" >&2; \
		exit 1; \
	}

list-quadlet-unit-files:
	systemctl --user list-unit-files | grep "^kaleido-api"

start:
	systemctl --user enable --now kaleido-api-nginx.service
	systemctl --user enable --now kaleido-api-cloudflared.service

fmt-python:
	uv run isort src/ scripts/
	uv run black src/ scripts/

.PHONY: \
	create-quadlet \
	check-secret \
	register-secret \
	deploy-quadlet \
	list-quadlet-unit-files \
	start \
	message
