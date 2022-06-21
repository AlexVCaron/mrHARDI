# docker-bake.hcl

group "default" {
    targets = ["latest"]
}

group "dependencies" {
    targets = ["base", "fsl", "mrtrix", "diamond", "ants", "dependencies"]
}

group "nogpu" {
    targets = ["scilpy", "nogpu"]
}

target "base" {
    dockerfile = "base/base_image.Dockerfile"
    output = ["type=cacheonly"]
}

target "cmake" {
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "base/cmake_builder.Dockerfile"
    output = ["type=cacheonly"]
}

target "web_fetcher" {
    dockerfile = "base/web_fetcher.Dockerfile"
    output = ["type=cacheonly"]
}

target "fsl" {
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "dependencies/builders/fsl.Dockerfile"
    output = ["type=cacheonly"]
}

target "mrtrix" {
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "dependencies/builders/mrtrix.Dockerfile"
    output = ["type=cacheonly"]
}

target "diamond" {
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "dependencies/builders/diamond.Dockerfile"
    output = ["type=cacheonly"]
}

target "ants" {
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "dependencies/builders/ants.Dockerfile"
    output = ["type=cacheonly"]
}

target "dependencies" {
    contexts = {
        base_image = "target:base"
        web_fetcher = "target:web_fetcher"
        fsl_builder = "target:fsl"
        ants_builder = "target:ants"
        diamond_builder = "target:diamond"
        mrtrix_builder = "target:mrtrix"
    }
    dockerfile = "dependencies/Dockerfile"
    tags = ["docker.io/avcaron/mrhardi:dependencies"]
    cache-from = ["avcaron/mrhardi:dependencies"]
    pull = true
}

target "scilpy" {
    contexts = {
        web_fetcher = "target:web_fetcher"
        dependencies = "target:dependencies"
    }
    dockerfile = "nogpu/builders/scilpy.Dockerfile"
    output = ["type=cacheonly"]
}

target "nogpu" {
    contexts = {
        web_fetcher = "target:web_fetcher"
        scilpy_installed = "target:scilpy"
    }
    dockerfile = "nogpu/Dockerfile"
    tags = ["docker.io/avcaron/mrhardi:nogpu"]
    no-cache = true
}

target "latest" {
    contexts = {
        nogpu = "target:nogpu"
    }
    dockerfile = "nvidia/Dockerfile"
    tags = [
        "docker.io/avcaron/mrhardi:gpu",
        "docker.io/avcaron/mrhardi:latest"
    ]
}