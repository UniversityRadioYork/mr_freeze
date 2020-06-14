import logging

from aiohttp.web_routedef import RouteTableDef
from aiohttp.web import Request, Response
import asyncpg
from typing import Optional

from config import cfg

logger = logging.getLogger("stats")
conn: Optional[asyncpg.Connection] = None


async def init():
    global conn
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
    params = await req.post()
    try:
        mount = params["mount"]
        client = params["client"]
        ip = params["ip"]
        agent = params["agent"]
    except KeyError as e:
        logger.error("Bad request - {}".format(repr(e)))
        return Response(status=400, text="Bad request", headers={"Icecast-Auth-Message": "bad_request"})

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

    header_name, header_value = cfg.get("stats", "response_header").split(": ")
    return Response(status=200, headers={
        header_name: header_value
    })


@routes.post("/listener_remove")
async def listener_remove(req: Request) -> Response:
    global conn
    params = await req.post()
    try:
        mount = params["mount"]
        client = params["client"]
        duration = params["duration"]
    except KeyError as e:
        logger.error("Bad request - {}".format(repr(e)))
        return Response(status=400, text="Bad request", headers={"Icecast-Auth-Message": "bad_request"})

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

    return Response(200)