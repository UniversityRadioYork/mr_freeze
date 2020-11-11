import logging

from aiohttp.web_routedef import RouteTableDef
from aiohttp.web import Request, Response
import asyncpg
from typing import Optional

from config import cfg

logger = logging.getLogger("stats")
conn: Optional[asyncpg.Connection] = None


async def init() -> None:
    global conn
    if conn is None or conn.is_closed():
        conn = await asyncpg.connect(
            host=cfg.get("stats", "pg_host"),
            user=cfg.get("stats", "pg_user"),
            password=cfg.get("stats", "pg_password"),
            database=cfg.get("stats", "pg_database")
        )


routes = RouteTableDef()


@routes.post("/listener_add")
async def listener_add(req: Request) -> Response:
    global conn
    await init()
    params = await req.post()
    try:
        mount = params["mount"]
        client = params["client"]
        ip = params["ip"]
        agent = params["agent"]
        header_name, header_value = cfg.get("stats", "response_header").split(": ")
    except KeyError as e:
        logger.error("Bad request - {}".format(repr(e)))
        return Response(status=400, text="Bad request", headers={"Icecast-Auth-Message": "bad_request"})

    # Check the allow/disallow lists
    only_accept_from = []
    if cfg.get("stats", "only_accept_from", fallback=None) is not None:
        only_accept_from = [x.strip() for x in cfg.get("stats", "only_accept_from").split(",")]

    ignore_from = []
    if cfg.get("stats", "ignore_from", fallback=None) is not None:
        ignore_from = [x.strip() for x in cfg.get("stats", "ignore_from".split(","))]

    if len(only_accept_from) > 0:
        if ip not in only_accept_from:
            return Response(status=200, headers={
                header_name: header_value
            })

    if ip in ignore_from:
        return Response(status=200, headers={
            header_name: header_value
        })

    await conn.execute(
        """
        INSERT INTO listens.listen (mount, client_id, ip_address, user_agent, time_start, time_end)
        VALUES ($1, $2, $3::inet, $4, NOW(), NULL)
        """,
        mount,
        client,
        ip,
        agent
    )

    return Response(status=200, headers={
        header_name: header_value
    })


@routes.post("/listener_remove")
async def listener_remove(req: Request) -> Response:
    global conn
    await init()
    params = await req.post()
    try:
        mount = params["mount"]
        client = params["client"]
        duration = params["duration"]
    except KeyError as e:
        logger.error("Bad request - {}".format(repr(e)))
        return Response(status=400, text="Bad request", headers={"Icecast-Auth-Message": "bad_request"})

    # Kill listens that were alive for only a few seconds
    min_listen_time = float(cfg.get("stats", "min_listen_time"))

    if float(duration) < min_listen_time:
        await conn.execute(
            "DELETE FROM listens.listen WHERE mount = $1 AND client_id = $2",
            mount,
            client
        )
    else:
        await conn.execute(
            """
            UPDATE listens.listen
            SET time_end = time_start + ($3 || ' seconds')::INTERVAL
            WHERE mount = $1 AND client_id = $2
            """,
            mount,
            client,
            duration
        )

    return Response(status=200)
