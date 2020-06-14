import asyncio

from aiohttp import web

import logging

from config import cfg

logging.basicConfig(level=logging.DEBUG, filename=cfg.get("mr_freeze", "debug_log_file"),
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

app = web.Application()

if cfg.has_section("auth") and cfg.get("auth", "enabled") == "1":
    from auth import routes as auth_routes
    app.add_routes(auth_routes)

if cfg.has_section("stats") and cfg.get("stats", "enabled") == "1":
    from stats import routes as stats_routes, init as stats_init
    asyncio.get_event_loop().run_until_complete(stats_init())
    app.add_routes(stats_routes)

web.run_app(app)
