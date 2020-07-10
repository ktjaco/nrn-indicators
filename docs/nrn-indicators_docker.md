# Getting Started with Docker

## Build the Docker image.
`$ docker build --network=host -t nrn-indicators .`

## Run the Docker image to enter an interactive shell.
`$ docker run --network=host --rm -v $PWD:/work -it nrn-indicators /bin/sh`