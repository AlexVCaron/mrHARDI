# docker-bake.hcl

group "default" {
    targets = ["mrhardi"]
}

target "release-tagging" {
    tags = ["mrhardi:local"]
}

target "base" {
    context = "base/."
    dockerfile = "base_image.Dockerfile"
    target = "base_image"
    output = ["type=cacheonly"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-base"]
}

target "cmake" {
    context = "base/."
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "cmake_builder.Dockerfile"
    target = "cmake_builder"
    output = ["type=cacheonly"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-cmake"]
}

target "web_fetcher" {
    context = "base/."
    dockerfile = "web_fetcher.Dockerfile"
    target = "web_fetcher"
    output = ["type=cacheonly"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-web-fetcher"]
}

target "diamond" {
    context = "dependencies/builders/."
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "diamond.Dockerfile"
    target = "diamond_builder"
    output = ["type=cacheonly"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-diamond"]
}

target "dependencies" {
    context = "dependencies/."
    contexts = {
        base_image = "docker-image://scilus/scilus:1.5.0"
        web_fetcher = "target:web_fetcher"
        diamond_builder = "target:diamond"
    }
    dockerfile = "Dockerfile"
    target = "dependencies"
    tags = ["docker.io/avcaron/mrhardi:dependencies"]
    pull = true
    output = ["type=image"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-dependencies"]
}

target "scilpy" {
    context = "mrhardi/builders/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        dependencies = "target:dependencies"
    }
    dockerfile = "scilpy.Dockerfile"
    target = "scilpy_installed"
    output = ["type=cacheonly"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-scilpy"]
}

target "mrhardi_cloner" {
    context = "mrhardi/."
    contexts = {
        web_fetcher = "target:web_fetcher"
    }
    dockerfile = "Dockerfile"
    target = "mrhardi_cloner"
    output = ["type=cacheonly"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi-cloner"]
}

target "mrhardi" {
    inherits = ["release-tagging"]
    context = "mrhardi/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        scilpy_installed = "target:scilpy"
        mrhardi_cloner = "target:mrhardi_cloner"
    }
    dockerfile = "Dockerfile"
    target = "mrhardi"
    output = ["type=docker"]
    cache-from = ["type=registry,ref=avcaron/build-cache:mrhardi"]
}
