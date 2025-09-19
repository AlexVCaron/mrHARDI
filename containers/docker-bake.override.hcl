# cache-push.hcl

target "base" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-base"]
}

target "cmake" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-cmake"]
}

target "web_fetcher" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-web-fetcher"]
}

target "diamond" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-diamond"]
}

target "dependencies" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-dependencies"]
}

target "scilpy" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-scilpy"]
}

target "mrhardi_cloner" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi-cloner"]
}

target "mrhardi" {
    cache-to = ["type=registry,mode=max,ref=avcaron/build-cache:mrhardi"]
}
