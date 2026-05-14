FROM shlinkio/shlink-web-client:stable
COPY servers.json.template /servers.json.template
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
