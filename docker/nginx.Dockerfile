FROM node:latest as js_dependencies

COPY demo/ui /dep/
WORKDIR /dep/
RUN npm clean-install
RUN npm run build

# Final image based on openresty
FROM openresty/openresty:1.21.4.1-0-alpine AS nginx

RUN apk update && apk --no-cache add tini

RUN rm -rf /etc/nginx/conf.d
COPY docker/nginx/run.sh /src/run.sh

ENV PATH=/src:$PATH
RUN chown -R nobody /etc/nginx /src
RUN mkdir -m 755 /var/log/nginx

COPY --from=js_dependencies /dep/dist /src/ui/demo/dist
COPY demo/ui/microsoft-identity-association.json /src/ui/microsoft-identity-association.json

WORKDIR /src/

EXPOSE 80
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/src/run.sh"]

COPY docker/nginx/nginx.conf /etc/nginx/conf.d/app.conf