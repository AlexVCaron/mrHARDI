FROM alpine:latest as build-image


FROM alpine:latest as light-image


FROM ubuntu:16.04 as deploy-nogpu


FROM deploy-nogpu as deploy-gnu
