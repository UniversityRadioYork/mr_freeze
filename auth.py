from typing import List, Dict, Optional
from aiohttp.web import Request, Response
from aiohttp.web_routedef import RouteTableDef
import logging
import bcrypt
from config import cfg

audit_file = logging.FileHandler(cfg.get("auth", "audit_log_file"))

logger = logging.getLogger("auth")
audit = logging.getLogger("auth.audit")
audit.addHandler(audit_file)

UserAttrs = Dict[str, str]


class User(object):
    def __init__(self, uname: str, passwd: str, attrs: UserAttrs):
        self.uname = uname
        self.passwd = passwd
        self.attrs = attrs


def load_users(path='users') -> List[User]:
    result = []
    with open(path, "r") as fd:
        for line in fd.readlines():
            uname_pw_pair, *attr_strs = line.split(" ")
            uname, pwhash = uname_pw_pair.split(":")
            attrs = {}
            for pair in attr_strs:
                key, val = pair.split("=")
                attrs[key] = val
            result.append(User(uname, pwhash.encode("utf-8"), attrs))
    return result


users_cache: Optional[List[User]] = None


def get_users() -> List[User]:
    global users_cache
    if users_cache is None:
        users_cache = load_users()
    return users_cache


routes = RouteTableDef()


@routes.post("/stream_auth")
async def handle_stream_auth(request: Request) -> Response:
    params = await request.post()
    users = get_users()

    try:
        username = params["user"]
        password = params["pass"]
        mount = params["mount"]
        server = params["server"]
        port = params["port"]
        ip = params["ip"]
        try:
            admin = params["admin"] == "1"
        except KeyError:
            admin = False
    except KeyError as e:
        logger.error("Bad request - {}".format(repr(e)))
        return Response(status=400, text="Bad request", headers={"Icecast-Auth-Message": "bad_request"})

    logger.info("Authentication request from {}@{} to {}:{}{} {}".format(username, ip, server, port, mount,
                                                                          "(admin)" if admin else ""))

    user: Optional[User] = None
    for test in users:
        if test.uname == username:
            user = test
            break

    if user is None:
        logger.info("Rejecting - no such user")
        audit.warning("{}@{} to {}:{}{} {} allowed=no reason=no_such_user".format(username, ip, server, port, mount,
                                                                                   "admin=yes" if admin else "admin=no"))
        return Response(status=403, text="No such user", headers={"Icecast-Auth-Message": "no_such_user"})

    if not bcrypt.checkpw(password.encode("utf-8"), user.passwd):
        logger.info("Rejecting - invalid password")
        audit.warning(
            "{}@{} to {}:{}{} {} allowed=no reason=incorrect_password".format(username, ip, server, port, mount,
                                                                               "admin=yes" if admin else "admin=no"))
        return Response(status=403, text="Incorrect password", headers={"Icecast-Auth-Message": "incorrect_password"})

    # Now check mount level permissions
    if "mounts" in user.attrs:
        valid_mounts = user.attrs["mounts"].split(",")
        if mount not in valid_mounts:
            logger.info("Rejecting - not permitted mount")
            audit.warning(
                "{}@{} to {}:{}{} {} allowed=no reason=forbidden_mount".format(username, ip, server, port, mount,
                                                                                "admin=yes" if admin else "admin=no"))
            return Response(status=403, headers={"Icecast-Auth-Message": "forbidden_mount"})

    # TODO server auth
    if "audit" in user.attrs:
        audit.info("{}@{} to {}:{}{} {} allowed=yes".format(username, ip, server, port, mount,
                                                             "admin=yes" if admin else "admin=no"))

    header_name, header_value = cfg.get("auth", "response_header").split(": ")
    return Response(status=200, headers={
        header_name: header_value
    })
