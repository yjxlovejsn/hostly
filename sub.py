import base64
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlparse

SECRET_KEY = os.environ["SUB_KEY"]
UUID = os.environ["UUID"]
HOST_DOMAIN = os.environ["HOST_DOMAIN"]
NODE_NAME = os.environ.get("NODE_NAME", "Pickle Hostly Germany Nuremberg")
GROUP_NAME = os.environ.get("GROUP_NAME", "Pickle Self-built Nodes")
TOTAL_BYTES = int(os.environ.get("TOTAL_BYTES", "1099511627776"))


def read_net_bytes():
    try:
        with open("/sys/class/net/eth0/statistics/rx_bytes") as f:
            rx = int(f.read().strip())
        with open("/sys/class/net/eth0/statistics/tx_bytes") as f:
            tx = int(f.read().strip())
        return rx, tx
    except Exception:
        return 0, 0


def next_reset_ts(reset_day=27):
    now = datetime.now(timezone.utc)
    if now.day < reset_day:
        nxt = datetime(now.year, now.month, reset_day, tzinfo=timezone.utc)
    elif now.month == 12:
        nxt = datetime(now.year + 1, 1, reset_day, tzinfo=timezone.utc)
    else:
        nxt = datetime(now.year, now.month + 1, reset_day, tzinfo=timezone.utc)
    return int(nxt.timestamp())


class SubHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path != "/sub" or qs.get("k", [""])[0] != SECRET_KEY:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        rx, tx = read_net_bytes()
        expire_ts = next_reset_ts(27)
        vless = (
            f"vless://{UUID}@{HOST_DOMAIN}:443"
            f"?encryption=none&security=tls&sni={HOST_DOMAIN}"
            f"&type=ws&host={HOST_DOMAIN}&path=%2Fvlessws#{quote(NODE_NAME)}"
        )
        body = base64.b64encode(vless.encode("utf-8"))
        title_b64 = base64.b64encode(GROUP_NAME.encode("utf-8")).decode("ascii")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Profile-Title", f"base64:{title_b64}")
        self.send_header(
            "Subscription-Userinfo",
            f"upload={rx}; download={tx}; total={TOTAL_BYTES}; expire={expire_ts}",
        )
        self.send_header("Profile-Update-Interval", "1")
        self.send_header("Content-Disposition", f'attachment; filename="{GROUP_NAME}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 10001), SubHandler).serve_forever()
