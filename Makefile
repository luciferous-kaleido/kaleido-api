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
	printf '%s' "$$CF_TUNNEL_TOKEN" | podman secret create --replace cf_tunnel_token -

.PHONY: \
	create-quadlet \
	check-secret \
	register-secret \
	message
