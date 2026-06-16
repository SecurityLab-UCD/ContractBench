from __future__ import annotations

import argparse
import os

import uvicorn

from .app import WebEphemeralConfig, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TGA WebEphemeral FastAPI app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--base-url", default=None, help="Advertised base URL for presigned links")
    parser.add_argument(
        "--max-request-target-bytes",
        type=int,
        default=None,
        help="If set, reject requests above this length with 414 (proxy simulation).",
    )
    args = parser.parse_args()

    base_url = args.base_url or f"http://{args.host}:{args.port}"
    secret = os.environ.get("TGA_PRESIGN_SECRET", "tga-dev-secret").encode("utf-8")
    app = create_app(
        WebEphemeralConfig(
            base_url=base_url,
            secret_key=secret,
            max_request_target_bytes=args.max_request_target_bytes,
        )
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
