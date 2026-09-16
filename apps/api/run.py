"""Development server entrypoint.

    python run.py [--host 127.0.0.1] [--port 8000] [--reload]

Exists because of Windows. psycopg's async driver refuses to run on a
ProactorEventLoop, and uvicorn hard-codes exactly that loop on win32
(``uvicorn/loops/asyncio.py::asyncio_loop_factory``) rather than honouring the
event loop policy -- so neither ``asyncio.set_event_loop_policy`` nor the
``--loop`` flag helps. Serving on an explicitly constructed SelectorEventLoop
is the only reliable fix.

The reload supervisor runs the server in a subprocess, which uvicorn already
gives a SelectorEventLoop, so that path can use the normal entrypoint.

On Linux and macOS ``uvicorn app.main:app --reload --port 8000`` is equivalent.
"""
import argparse
import asyncio
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.reload or sys.platform != "win32":
        uvicorn.run(
            "app.main:app", host=args.host, port=args.port, reload=args.reload
        )
        return

    server = uvicorn.Server(
        uvicorn.Config("app.main:app", host=args.host, port=args.port)
    )
    loop = asyncio.SelectorEventLoop()
    try:
        loop.run_until_complete(server.serve())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
