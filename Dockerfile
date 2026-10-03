# talk-sip-bridge - container image
#
# Lightweight image that runs the talk-sip-bridge daemon from
# https://github.com/schnebeck/talk-sip-bridge. All configuration is done
# through environment variables - see docs/CONFIG.md in the upstream
# repository for the complete reference, and .env.example here for the
# required subset.
#
# The daemon is GPL-3.0-or-later; see the upstream LICENSE file.

FROM python:3.12-slim

# A pinned upstream commit keeps the image reproducible. Bump TSB_REF (and
# REBUILD) to track the upstream project.
ARG TSB_REPOSITORY=https://github.com/schnebeck/talk-sip-bridge.git
ARG TSB_REF=4ecb0f3e98bdaa19cfa4bb26dead873a3d12cc31

# git fetches the pinned source; ca-certificates stays for the image's
# wss:// signaling and https:// Nextcloud connections. No compiler is
# needed: av, numpy and aiortc ship manylinux wheels.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && git init -q /usr/src/talk-sip-bridge \
 && git -C /usr/src/talk-sip-bridge remote add origin "$TSB_REPOSITORY" \
 && git -C /usr/src/talk-sip-bridge fetch -q --depth 1 origin "$TSB_REF" \
 && git -C /usr/src/talk-sip-bridge checkout -q FETCH_HEAD \
 && apt-get purge -y git \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/* /usr/src/talk-sip-bridge/.git

# The daemon imports its sibling modules (`from config import config`), so
# they must live in the script's directory / on the working directory.
WORKDIR /opt/talk-sip-bridge

RUN cp /usr/src/talk-sip-bridge/bridge/*.py /opt/talk-sip-bridge/ \
 && cp /usr/src/talk-sip-bridge/bridge/requirements.txt /opt/talk-sip-bridge/ \
 && rm -rf /usr/src/talk-sip-bridge \
 && pip install --no-cache-dir -r requirements.txt \
 && rm -f requirements.txt

# Small per-line state files (whether each line's registration should be on).
VOLUME /var/lib/talk-sip-bridge

ENV PYTHONUNBUFFERED=1

# Local SIP and RTP ports of a single-line deployment, plus the control API.
EXPOSE 5060/udp 40000/udp 8765/tcp

ENTRYPOINT ["python3", "-u", "/opt/talk-sip-bridge/daemon.py"]