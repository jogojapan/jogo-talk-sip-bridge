This is a project for creating and running a Docker container image
that wraps the talk-sip-bridge defined in
https://github.com/schnebeck/talk-sip-bridge.

It's a lightweight image with minimal components necessary to run the
bridge and configure it through environment variables.

## Repository layout

- `Dockerfile` - builds the image. It clones the upstream repo at a
  pinned commit (`ARG TSB_REF`), installs the bridge's own deps in the
  base `python:3.12-slim` image (manylinux wheels, no compiler), and runs
  `daemon.py` from `/opt/talk-sip-bridge`. State lives in
  `/var/lib/talk-sip-bridge` (a `VOLUME`).
- `docker-compose.yml.example` - run config; pass `.env` straight through
  with `env_file` (no variable expansion, so any `BRIDGE_*` setting works
  unmodified). Defaults to `network_mode: host`; `ports:` alternative is
  commented out.
- `.env.example` - the 7 required bridge variables plus optional ones.
- `README.md` - setup in Portainer/Docker, Talk-side `occ` config, and
  networking notes.
- `LICENSE` (MIT) - covers only this repo's own files. The wrapped bridge
  stays GPL-3.0-or-later; the built image carries that code under GPL.

## Conventions and decisions

- All bridge configuration is via environment variables; never hardcode a
  bridge value in the Dockerfile or compose.
- Network mode is `host` because the daemon binds its SIP/RTP sockets to
  `BRIDGE_LOCAL_IP` (an ordinary LAN host address); NAT breaks that.
  `BRIDGE_CONTROL_BIND` defaults to `127.0.0.1` and is documented for the
  cross-network case.
- `TSB_REF` pins the upstream commit; bump it (and rebuild) to track
  upstream. Do not copy upstream source into this repo - build pulls it.
- `.gitignore` keeps `.env`, `docker-compose.yml`, Python artifacts, and
  OS/editor junk out of the tree; `.dockerignore` trims the build context
  (the build fetches source inside the image, so the context is unused).

## Verification

After any change to the image/entrypoint, build and smoke-test the daemon:
run the container with fake env, exercise `GET /status` and
`POST /toggle` on the control API, then clean up container and image.