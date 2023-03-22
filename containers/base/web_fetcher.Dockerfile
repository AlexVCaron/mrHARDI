# syntax=docker/dockerfile:1.4

FROM alpine:latest AS web_fetcher

RUN apk add --no-cache wget
RUN apk add --no-cache git
RUN apk add --no-cache unzip
