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
}

target "cmake" {
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "base/cmake_builder.Dockerfile"
}

target "web_fetcher" {
    dockerfile = "base/web_fetcher.Dockerfile"
}

target "fsl" {
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "dependencies/builders/fsl.Dockerfile"
}

target "mrtrix" {
    contexts = {
        base_image = "target:base"
    }
    dockerfile = "dependencies/builders/mrtrix.Dockerfile"
}

target "diamond" {
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "dependencies/builders/diamond.Dockerfile"
}

target "ants" {
    contexts = {
        cmake_builder = "target:cmake"
    }
    dockerfile = "dependencies/builders/ants.Dockerfile"
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
}

target "scilpy" {
    contexts = {
        web_fetcher = "target:web_fetcher"
        dependencies = "target:dependencies"
    }
    dockerfile = "nogpu/builders/scilpy.Dockerfile"
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