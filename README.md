# talk-sip-bridge container

A lightweight Docker image that wraps
[`talk-sip-bridge`](https://github.com/schnebeck/talk-sip-bridge), the open
implementation of Nextcloud Talk's phone bridge interface. It lets people
join a Talk call by telephone, and lets Talk*Call a phone number* ring a
phone. All configuration is done through environment variables.

The image holds only the pieces needed to run the bridge: the daemon,
its Python dependencies, and two dirs - `/opt/talk-sip-bridge` for the
code and `/var/lib/talk-sip-bridge` for small per-line state (which lines
should be registered).

## What you need

- A SIP phone account (username, password, address of the gateway).
- A Nextcloud with Talk *and* a separate signaling server (the High
  Performance Backend; the built-in signaling server cannot do this).
- A Linux host running Docker that reaches both the gateway and the
  signaling server.

## Quick start

```
cp .env.example .env     # fill in the values
cp docker-compose.yml.example docker-compose.yml
docker compose up -d --build
curl http://127.0.0.1:8765/status
```

The line starts off unregistered. Turn it on from the Nextcloud admin page
(if you installed the companion app) or:

```
curl -X POST http://127.0.0.1:8765/toggle
```

`"registered": true, "last_error": null` means the line is up. Then open a
Talk conversation, start a call, and press *Call a phone number*.

## Configuration

Everything goes in `.env` (a copy of [`.env.example`](./.env.example)),
which `docker compose` passes straight through. The required values are:

```
BRIDGE_SIP_USER=
BRIDGE_SIP_PASS=
BRIDGE_GATEWAY_HOST=
BRIDGE_LOCAL_IP=
BRIDGE_WS_URL=
BRIDGE_INTERNAL_SECRET=
BRIDGE_BACKEND_URL=
```

`BRIDGE_LOCAL_IP` must be an address of **this host** that the daemon can
bind SIP/RTP to (see networking below). The other two tunnels of the bridge
are documented there; the upstream
[`docs/CONFIG.md`](https://github.com/schnebeck/talk-sip-bridge/blob/main/docs/CONFIG.md)
is the full reference for every variable, including multi-line accounts
(`BRIDGE_LINES` / `BRIDGE_LINE_<id>_*`).

### Talk side

For Talk's phone UI and virtual phone participants to work at all, three
`spreed` app config values must be set:

```
occ config:app:set spreed sip_bridge_shared_secret --value="$(openssl rand -hex 32)"
occ config:app:set spreed sip_bridge_dialin_info   --value='<the number to call>'
occ config:app:set spreed sip_dialout              --value='yes'
```

`BRIDGE_INTERNAL_SECRET` here must equal `sip_bridge_shared_secret`.

## Networking

The daemon binds its SIP and RTP sockets to `BRIDGE_LOCAL_IP` as an
ordinary LAN host; the gateway must reach that address directly. That is
why the example compose file uses `network_mode: host`: no NAT in the
middle of the SIP/RTP path. Consequences:

- The bridge listens on the host's `5060` (SIP) and `40000` (RTP), so those
  ports must be free on the host.
- With Nextcloud on the same host, the default `BRIDGE_CONTROL_BIND=127.0.0.1`
  works. If Nextcloud runs in its own container/network, bind the control
  API to an address that container/host can reach (a private Docker bridge
  gateway address) - never a public interface. See the compose example for
  the published-port alternative if you need namespace isolation.

## Building from source

`TSB_REF` in the `Dockerfile` pins the upstream commit; bump it (and
rebuild) to track the upstream project. `docker compose up -d --build`
rebuilds from the current tree.

## Upstream documents

- [`docs/CONFIG.md`](https://github.com/schnebeck/talk-sip-bridge/blob/main/docs/CONFIG.md) - every setting
- [`docs/ADMIN.md`](https://github.com/schnebeck/talk-sip-bridge/blob/main/docs/ADMIN.md) - install, check, fix
- [`docs/REFERENCE-CALL.md`](https://github.com/schnebeck/talk-sip-bridge/blob/main/docs/REFERENCE-CALL.md) - what a working call looks like

Licensing: this wrapper's own files are MIT licensed - see [`LICENSE`](./LICENSE).
The talk-sip-bridge software the image runs is GPL-3.0-or-later (see the
upstream [`LICENSE`](https://github.com/schnebeck/talk-sip-bridge/blob/main/LICENSE));
it keeps that license inside the built image, and distributing the image
carries the GPL's source-availability obligations for it.