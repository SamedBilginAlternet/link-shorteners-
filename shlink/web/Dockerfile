FROM shlinkio/shlink-web-client:stable
COPY servers.json.template /servers.json.template
CMD ["sh", "-c", "sed -e \"s|__SHLINK_URL__|${SHLINK_PUBLIC_URL}|g\" -e \"s|__SHLINK_API_KEY__|${SHLINK_API_KEY}|g\" /servers.json.template > /usr/share/nginx/html/servers.json && exec nginx -g 'daemon off;'"]
