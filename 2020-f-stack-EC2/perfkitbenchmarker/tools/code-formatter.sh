#!/bin/bash

FILE_TO_FORMAT=$1
PYTHON=${2:-/usr/bin/python2}
VENV_DIR=${3:-/tmp/pkb-formatter-venv-$(date '+%Y%m%d%H%M%S%N')}
LOG_FILE=${4:-/tmp/pkb-formatter-$(date '+%Y%m%d%H%M%S%N').log}


function print_usage() {
  echo "
  Usage: $0 filename_to_format [python_binary] [venv_dir] [log_file]
  PerfKitBenchmarker code formatter

  Optional arguments:
    python_binary   the full path to the Python binary you want to use
                    example: /usr/bin/python2
    venv_dir        the virtualenv you want to use for the formatting process.
                    If you chose this you are fully responsible for the content
                    and the libraries installed inside it
    log file        the log file where stdout and stderr for every command will
                    be dumped
  "
}


function log() {
  TIMESTAMP=$(date '+%F %T')
  echo "[${TIMESTAMP}] $1" | tee -a ${LOG_FILE}
}


function check_input() {
  if [ -z "${FILE_TO_FORMAT}" ]; then
    echo "Please supply the filename to format!"
    print_usage
    exit
  fi

  if test -f "${FILE_TO_FORMAT}"; then
    log "File ${FILE_TO_FORMAT} found!"
  else
    log "File ${FILE_TO_FORMAT} not found! Please choose a valid file!"
    exit
  fi
}


function is_binary_found() {
  BINARY=$1
  which ${BINARY} &>> ${LOG_FILE}
  return $?
}


function enable_venv() {
  if [ -d "${VENV_DIR}" ]; then
    log "Activating virtualenv for formatting"
    source ${VENV_DIR}/bin/activate &>> ${LOG_FILE}
  else
    log "Virtualenv directory ${VENV_DIR} not found"
    if ! is_binary_found "virtualenv"; then
      log "    Installing virtualenv binary. You might need to provide the sudo password"
      sudo $(PYTHON) -m pip install virtualenv | tee -a ${LOG_FILE}
    fi
    
    log "    Creating ${VENV_DIR}"
    virtualenv -p ${PYTHON} ${VENV_DIR} &>> ${LOG_FILE}

    log "    Activating virtualenv for formatting"
    source ${VENV_DIR}/bin/activate &>> ${LOG_FILE}

    log "    Installing dependencies"
    log "        Installing AUTOPEP8"
    pip install autopep8==1.4.4 &>> ${LOG_FILE}
    log "        Installing TOX"
    pip install tox==3.12.1 &>> ${LOG_FILE}
  fi
}


function clean_tree() {
  log "Cleaning tree"
  rm -rf .tox/
  find . -name '*.py[co]' -exec rm -f {} ';'
}


function run_formatter() {
  log "Formatting file. Please wait until done!"
  FILE=$1
  ${PYTHON} -m autopep8 --global-config .autopep8.cfg --recursive --in-place --jobs 0 --verbose --aggressive --aggressive $FILE &>> ${LOG_FILE}
}


function check_result() {
  log "Running checks"
  export TOX_ENV=flake8
  python $(which tox) -e ${TOX_ENV}
}


### Main ###
check_input
rm -f ${LOG_FILE}
log "Using Python: ${PYTHON}"
log "Using virtualenv: ${VENV_DIR}"
log "Logging everything to ${LOG_FILE}"
enable_venv
clean_tree
run_formatter $FILE_TO_FORMAT
check_result
clean_tree
