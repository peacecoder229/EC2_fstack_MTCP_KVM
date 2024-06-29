#!/bin/bash

DOCKER_IMAGE=python

case $1 in
2*)
  DOCKER_TAG=2.7-buster
  TOX_ENV=py27,flake8,scripts
  ;;
3*)
  DOCKER_TAG=3.7-buster
  TOX_ENV=py37,flake8,scripts
  ;;
*)
  echo "Wrong input parameter!"
  echo "Usage: tools/full-checker PYTHON_MAJOR_VERSION, where PYTHON_MAJOR_VERSION can be 2 or 3"
  exit
  ;;
esac

EXTRA_CLEAN_CMD="rm -rf .tox ; find . -name '*.py[co]' -exec rm -f {} ';'"
CHECK_CMD="$EXTRA_CLEAN_CMD ; pip install tox ; tox -r -e $TOX_ENV ; $EXTRA_CLEAN_CMD"

COMMITID=$(git log -1 | head -n 1 | awk '{print $2}')
TIMESTAMP=$(date +%Y%m%d)
DOCKER_CONTAINER="$DOCKER_IMAGE:$DOCKER_TAG"
LOG_FILE="full-checker-$TIMESTAMP-$DOCKER_TAG-$COMMITID.log"

echo "Pulling Docker image:      $DOCKER_CONTAINER"
docker pull $DOCKER_CONTAINER &> /dev/null

echo "Running checker. Log file: $LOG_FILE"
docker run --rm -it -v "$(pwd)":/pkb -w /pkb $DOCKER_CONTAINER /bin/bash -c "$CHECK_CMD" &> $LOG_FILE

RETCODE=$(tail -n 4 $LOG_FILE | grep "ERROR" | wc -l)

echo "Done with retcode:         $RETCODE"
echo "Duration:                  $SECONDS seconds"

exit $RETCODE
