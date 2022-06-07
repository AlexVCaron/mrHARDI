# docker-bake.hcl

group "default" {
    targets = ["latest"]
}

group "dependencies" {
    targets = ["dependencies"]
}

group "nogpu" {
    targets = ["nogpu"]
}

target "dependencies" {
    dockerfile = "dependencies/Dockerfile"
    tags = ["docker.io/avcaron/mrhardi:dependencies"]
}

target "nogpu" {
    contexts = {
        baseapp = "target:dependencies"
    }
    dockerfile = "nogpu/Dockerfile"
    tags = ["docker.io/avcaron/mrhardi:nogpu"]
    no-cache = true
}

target "latest" {
    contexts = {
        baseapp = "target:nogpu"
    }
    dockerfile = "nvidia/Dockerfile"
    tags = [
        "docker.io/avcaron/mrhardi:gpu",
        "docker.io/avcaron/mrhardi:latest"
    ]
}