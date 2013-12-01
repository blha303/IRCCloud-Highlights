import requests
import time
import json
import sys
import websocket
from colorama import init as crinit
from colorama import Fore, Style
from fnmatch import fnmatchcase

tmpcookie = "PUT COOKIE HERE"
delay = 0.0
idleinterval = 0
user = {}
servers = {}
buffers = {}
whois = {}


def uni2str(inp):
    return inp.encode('ascii', 'xmlcharrefreplace')


def auth(email, password):
    req = requests.post("https://www.irccloud.com/chat/login",
                        data={"email": email, "password": password})
    d = req.json()
    if d["success"]:
        return d["session"]
    else:
        return False


def streamiter(cookie):
    ws = websocket.create_connection("wss://www.irccloud.com/",
                                     header=["Cookie: session=%s" % cookie],
                                     origin="https://www.irccloud.com")
    while 1:
        msg = ws.recv()
        if msg:
            yield json.loads(msg)


def parseline(line):
    msgfmt = u"{time} {server}:{channel} <{nick}> {msg}"
    mefmt = u"{time} {server}:{channel} * {nick} {msg}"
    noticefmt = u"{time} {server}:{channel} -{nick}- {msg}"

    def getts(l):
        return time.gmtime(float(str(l["eid"])[:-6]+"."+str(l["eid"])[-6:]))

    def p_header(l):
        delay = int(time.time()) - l["time"]

    def p_stat_user(l):
        user.update(l)

    def p_num_invites(l):
        user["num_invites"] = l["num_invites"]

    def p_oob_include(l):
        req = requests.get("https://www.irccloud.com" + l["url"],
                           headers={"Cookie": "session=%s" % tmpcookie,
                                    "Accept-Encoding": "gzip"}).json()
        for oobline in req:
            try:
                parseline(oobline)
            except:
                print json.dumps(oobline)
                raise

    def p_makeserver(l):
        for b in user["highlights"]:
            for a in user["highlights"]:
                if a in b and a != b:
                    user["highlights"].remove(a) if len(a) < len(b) else user["highlights"].remove(b)
        if not l["cid"] in servers:
            servers[l["cid"]] = l
        else:
            servers[l["cid"]].update(l)

    def p_channel_init(l):
        if not l["bid"] in buffers:
            buffers[l["bid"]] = l
        else:
            buffers[l["bid"]].update(l)

    def p_connection_lag(l):
        servers[l["cid"]]["lag"] = l["lag"]

    def p_buffer_msg(l):
        for ignore in servers[l["cid"]]["ignores"]:
            if fnmatchcase(l["from"] + "!" + l["hostmask"], ignore):
                return
        ts = getts(l)
        if l["chan"] == servers[l["cid"]]["nick"]:
            l["msg"] = Fore.RED + l["msg"] + Fore.RESET
        else:
            for hl in user["highlights"]:
                if hl in l["msg"]:
                    l["msg"] = l["msg"].encode("ascii", "replace").replace(hl, Fore.RED + hl + Fore.RESET)
        print msgfmt.format(time=time.strftime("%H:%M:%S", ts),
                            server=servers[l["cid"]]["name"],
                            channel=l["chan"],
                            nick=l["from"],
                            msg=l["msg"]) if Fore.RED in l["msg"] else ""

    def p_notice(l):
        for ignore in servers[l["cid"]]["ignores"]:
            if fnmatchcase(l["from"] + "!" + l["hostmask"], ignore):
                return
        ts = getts(l)
        for hl in user["highlights"]:
            if hl in l["msg"]:
                l["msg"] = l["msg"].encode("ascii", "replace").replace(hl, Fore.RED + hl + Fore.RESET)
        print noticefmt.format(time=time.strftime("%H:%M:%S", ts),
                            server=servers[l["cid"]]["name"],
                            channel=l["chan"],
                            nick=l["from"],
                            msg=l["msg"]) if Fore.RED in l["msg"] else ""

    def p_channel_timestamp(l):
        buffers[l["bid"]]["timestamp"] = l["timestamp"]

    def p_self_details(l):
        data = {'server': l["server"],
                'ircserver': l["ircserver"],
                'away': l["away"],
                'ident_prefix': l["ident_prefix"]}
        servers[l["cid"]].update(data)

    def p_self_away(l):
        servers[l["cid"]]["away"] = l["away_msg"]

    def p_self_back(l):
        servers[l["cid"]]["away"] = False

    def p_rename_conversation(l):
        buffers[l["bid"]]["name"] = l["new_name"]

    def p_server_details_changed(l):
        p_makeserver(l)

    def p_set_ignores(l):
        servers[l["cid"]]["ignores"].extend(l["masks"])

    try:
        locals()["p_"+line["type"]](line)
    except KeyError:
        """ """


if __name__ == "__main__":
    crinit()
    if len(sys.argv) > 2 and "@" in sys.argv[1]:
        isauthed = auth(sys.argv[1], " ".join(sys.argv[2:]))
        if isauthed:
            tmpcookie = isauthed
        else:
            print "Unable to authenticate with email " + sys.argv[1]
            sys.exit(2)
    elif (tmpcookie == "PUT COOKIE HERE" and len(sys.argv) == 2
            and not "@" in sys.argv[1]):
        tmpcookie = sys.argv[1]
    elif tmpcookie == "PUT COOKIE HERE":
        print "Usage: highlights.py <cookie> | highlights.py <email> <password>"
        sys.exit(2)
    try:
        for line in streamiter(tmpcookie):
            parseline(line)
    except KeyboardInterrupt:
        sys.exit()
