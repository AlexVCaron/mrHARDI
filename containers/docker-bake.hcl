# docker-bake.hcl

group "default" {
    targets = ["nogpu", "latest"]
}

target "gpu-release-tagging" {
    tags = [
        "docker.io/avcaron/mrhardi-gpu:latest",
        "docker.io/avcaron/mrhardi:latest"
    ]
}

target "cpu-release-tagging" {
    tags = ["docker.io/avcaron/mrhardi-nogpu:latest"]
} 

target "base" {
    context = "base/."
    dockerfile = "base_image.Dockerfile"
    target = "base_image"
    output = ["type=cacheonly"]
}

target "cmake" {
    context = "base/."
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "cmake_builder.Dockerfile"
    target = "cmake_builder"
    output = ["type=cacheonly"]
}

target "web_fetcher" {
    context = "base/."
    dockerfile = "web_fetcher.Dockerfile"
    target = "web_fetcher"
    output = ["type=cacheonly"]
}

target "diamond" {
    context = "dependencies/builders/."
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "diamond.Dockerfile"
    target = "diamond_builder"
    output = ["type=cacheonly"]
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
    cache-from = ["avcaron/mrhardi:dependencies"]
    pull = true
    output = ["type=image"]
}

target "scilpy" {
    context = "nogpu/builders/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        dependencies = "target:dependencies"
    }
    dockerfile = "scilpy.Dockerfile"
    target = "scilpy_installed"
    output = ["type=cacheonly"]
}

target "mrhardi_cloner" {
    context = "nogpu/."
    contexts = {
        web_fetcher = "target:web_fetcher"
    }
    dockerfile = "Dockerfile"
    target = "mrhardi_cloner"
    output = ["type=cacheonly"]
}

target "nogpu" {
    inherits = ["cpu-release-tagging"]
    context = "nogpu/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        scilpy_installed = "target:scilpy"
        mrhardi_cloner = "target:mrhardi_cloner"
    }
    dockerfile = "Dockerfile"
    target = "nogpu"
    output = ["type=image"]
}

target "latest" {
    inherits = ["gpu-release-tagging"]
    contexts = {
        nogpu = "target:nogpu"
    }
    dockerfile = "nvidia/Dockerfile"
    target = "nvidia"
    output = ["type=image"]
}
