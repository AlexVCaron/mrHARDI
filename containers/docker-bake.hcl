# docker-bake.hcl

group "default" {
    targets = ["nogpu", "latest"]
}

group "dependencies" {
    targets = ["dependencies"]
}

group "full" {
    targets = ["dependencies", "nogpu-full", "latest-full"]
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

target "fsl" {
    context = "dependencies/builders/."
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "fsl.Dockerfile"
    target = "fsl_builder"
    output = ["type=cacheonly"]
}

target "mrtrix" {
    context = "dependencies/builders/."
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "mrtrix.Dockerfile"
    target = "mrtrix_builder"
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

target "ants" {
    context = "dependencies/builders/."
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "ants.Dockerfile"
    target = "ants_builder"
    output = ["type=cacheonly"]
}

target "dependencies" {
    context = "dependencies/."
    contexts = {
        base_image = "target:base"
        web_fetcher = "target:web_fetcher"
        fsl_builder = "target:fsl"
        ants_builder = "target:ants"
        diamond_builder = "target:diamond"
        mrtrix_builder = "target:mrtrix"
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
        dependencies = "docker-image://avcaron/mrhardi:dependencies"
    }
    dockerfile = "scilpy.Dockerfile"
    target = "scilpy_installed"
    output = ["type=cacheonly"]
}

target "nogpu" {
    context = "nogpu/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        scilpy_installed = "target:scilpy"
    }
    dockerfile = "Dockerfile"
    target = "nogpu"
    tags = ["docker.io/avcaron/mrhardi:nogpu"]
    no-cache = true
    output = ["type=image"]
}

target "latest" {
    contexts = {
        nogpu = "target:nogpu"
    }
    dockerfile = "nvidia/Dockerfile"
    target = "nvidia"
    tags = [
        "docker.io/avcaron/mrhardi:gpu",
        "docker.io/avcaron/mrhardi:latest"
    ]
    output = ["type=image"]
}

target "scilpy-full" {
    context = "nogpu/builders/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        dependencies = "target:dependencies"
    }
    dockerfile = "scilpy.Dockerfile"
    target = "scilpy_installed"
    output = ["type=cacheonly"]
}

target "nogpu-full" {
    context = "nogpu/."
    contexts = {
        web_fetcher = "target:web_fetcher"
        scilpy_installed = "target:scilpy-full"
    }
    dockerfile = "Dockerfile"
    target = "nogpu"
    tags = ["docker.io/avcaron/mrhardi-nogpu:latest"]
    no-cache = true
    output = ["type=image"]
}

target "latest-full" {
    contexts = {
        nogpu = "target:nogpu-full"
    }
    dockerfile = "nvidia/Dockerfile"
    target = "nvidia"
    tags = [
        "docker.io/avcaron/mrhardi-gpu:latest",
        "docker.io/avcaron/mrhardi:latest"
    ]
    output = ["type=image"]
}
