
dockerimg:
	/usr/bin/docker build  --no-cache -t="registry.met.no/modellprod/yeehaa-container:latest" .
dockerrun:
	docker run -v /lustre:/lustre -v $(PWD):$(PWD) -i -t registry.met.no/modellprod/yeehaa-container:latest /bin/bash

sif: dockerimg
	sudo singularity build mmd-container-latest.sif docker-daemon://registry.met.no/modellprod/yeehaa-container:latest		

sifshell:
	MET_WORKDIR=/tmp singularity exec --bind /lustre:/lustre/,$(HOME):$(HOME) mmd-container-latest.sif /bin/bash
