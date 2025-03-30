 #!/bin/bash         
docker build . --build-arg "GIT_USERNAME=$1" --build-arg "GIT_USER_EMAIL=$2" --build-arg "GIT_TOKEN=$3" -t convince_people_detector:jazzy -f Dockerfile
