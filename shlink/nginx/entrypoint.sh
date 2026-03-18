#!/bin/sh
htpasswd -bc /etc/nginx/.htpasswd "$NGINX_USER" "$NGINX_PASS"
exec nginx -g "daemon off;"
