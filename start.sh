#!/bin/sh
set -e

PORT="${PORT:-8080}"
UUID="${UUID:?UUID env var is required}"

cat <<EOF > /etc/xray/app-config.json
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "127.0.0.1",
      "port": 10000,
      "protocol": "vless",
      "settings": {
        "clients": [{ "id": "${UUID}" }],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": { "path": "/vlessws" }
      }
    }
  ],
  "outbounds": [{ "protocol": "freedom" }]
}
EOF

cat <<EOF > /etc/nginx/http.d/default.conf
server {
    listen ${PORT};
    listen [::]:${PORT};

    location / {
        return 200 "Service is running\n";
        add_header Content-Type text/plain;
    }

    location = /sub {
        proxy_pass http://127.0.0.1:10001;
        proxy_set_header Host \$host;
    }

    location /vlessws {
        if (\$http_upgrade != "websocket") {
            return 404;
        }
        proxy_redirect off;
        proxy_pass http://127.0.0.1:10000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

python3 /sub.py &
xray run -config /etc/xray/app-config.json &
exec nginx -g "daemon off;"
