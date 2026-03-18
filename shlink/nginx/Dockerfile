FROM nginx:alpine
RUN apk add --no-cache apache2-utils
COPY nginx.conf /etc/nginx/nginx.conf
CMD ["/bin/sh", "-c", "htpasswd -bc /etc/nginx/.htpasswd \"$NGINX_USER\" \"$NGINX_PASS\" && nginx -g 'daemon off;'"]
