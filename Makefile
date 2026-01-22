
dockerimg:
	/usr/bin/docker build  -t="registry.met.no/modellprod/yeehaa-container:latest" --build-arg SCRAPER_USERNAME=$(SCRAPER_USERNAME) --build-arg SCRAPER_PASSWORD=$(SCRAPER_PASSWORD) --build-arg SCRAPER_TOTP_SECRET=$(SCRAPER_TOTP_SECRET) .
dockerrun:
	docker run -v $(PWD):$(PWD) -i -t registry.met.no/modellprod/yeehaa-container:latest /bin/bash

sif: dockerimg
	sudo singularity build yeehaa-container-latest.sif docker-daemon://registry.met.no/modellprod/yeehaa-container:latest		

sifshell:
	MET_WORKDIR=/tmp singularity exec yeehaa-container-latest.sif /bin/bash
