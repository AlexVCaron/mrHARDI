# syntax=docker.io/docker/dockerfile:1.5-labs

FROM alpine:latest AS web_fetcher

RUN apk add --no-cache git
RUN apk add --no-cache unzip
