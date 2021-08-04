#!/usr/bin/env python3

##########
#
# Process incoming git webhooks and run a specified Salt state.
#
# Environment variable configuration:
#     GITHOOK_SECRET - Secret for validation of GitHub or GitLab payloads.
#     LOG_LEVEL      - (optional) Log level for app messages. Defaults to INFO.
#     SALT_STATE     - State name to run using the Caller client (salt-call).
#
# A "git_ref" key is passed in Pillar to the state in "refs/(heads|tags)/(name)" format.
#
##########

# Python libs
import hashlib
import hmac
import logging
from os import environ
from sys import stdout

# Third-party libs
try:
    import salt.client
    from flask import Flask, request, Response
except ImportError as exc:
    print(f"{exc}")
    exit(1)


app = Flask(__name__)

# Setup logging to stdout
log = logging.getLogger(__name__)
log_handler = logging.StreamHandler(stdout)
log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

try:
    log.setLevel(environ.get("LOG_LEVEL", "INFO"))
except:
    pass


def validate_github(payload, signature, secret):
    """
    Validate GitHub signature
    """
    secret = secret.encode()
    hmac_gen = hmac.new(secret, payload, hashlib.sha1)
    digest = "sha1=" + hmac_gen.hexdigest()

    if hmac.compare_digest(digest, signature):
        return True

    log.error(f"Failed GitHub validation (signature = {signature} | digest = {digest})")

    return False


@app.route("/webhook", methods=["POST"])
def process_webhook():
    """
    Process incoming git webhooks
    """
    try:
        state = environ["SALT_STATE"]
    except KeyError as exc:
        log.error(f"Salt state env var not defined ({exc})")
        exit(1)

    if request.json:
        log.debug(f"Request JSON: {request.json}")

        if "X-Hub-Signature" in request.headers:
            signature = request.headers["X-Hub-Signature"]
            secret = environ.get("GITHOOK_SECRET", "")
            ret = validate_github(request.data, signature, secret)
            if not ret:
                return Response(status=400)
        elif "X-GitLab-Token" in request.headers:
            token = request.headers["X-GitLab-Token"]
            secret = environ.get("GITHOOK_SECRET", "")
            if token != secret:
                log.error(f"Failed GitLab validation (token = {token})")
                return Response(status=400)

        ref = request.json.get("ref")
        pillar = {"git_ref": ref}
        caller = salt.client.Caller()
        ret = caller.cmd("state.apply", state, pillar=pillar)
        log.debug(f"Salt caller response: {ret}")

        results = []
        for name, items in ret.items():
            results.append(items["result"])

        if not all(results):
            log.error(f"State application failed ({ret})")
            return Response(status=400)

        log.info(f"Processed webhook for {ref}")
        return Response(status=200)

    return Response(status=400)
