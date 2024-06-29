#!/bin/bash

#
# This script will install the Python Django workload
# under ~/python-django/src/django-workload
#
# The script expects that a .zip archive containing the django workload
# is present in the directory containing this script. The .zip archive
# needs to respect the naming convention of tarballs downloaded from
# https://gitlab.devtools.intel.com/DCSP/Python/django-workload-internal
#
# e.g. django-workload-internal-$VERSION.zip
#
# where $VERSION represents the version tag (master or a particular release).
# $VERSION needs to be passed as a cmd line argument for this script.
#

if [ "$#" != 2 ]; then
    echo "Usage: ${0} django_wl_version webtier-provisioning_version"
    exit 255
fi

DJANGO_WL_INTERNAL_NAME="django-workload-internal"
DJANGO_WL_GENERIC_NAME="django-workload"
DJANGO_WL_VERSION="$1"
WEBTIER_PROV_NAME="webtier-provisioning"
WEBTIER_PROV_VERSION="$2"
WORKING_DIR=$(cd $(dirname "$0") && pwd)
WHOAMI=$(whoami)

if [ ! -f "$WORKING_DIR/$DJANGO_WL_INTERNAL_NAME-$DJANGO_WL_VERSION.zip" ]; then
    echo "ERROR: $WORKING_DIR/$DJANGO_WL_INTERNAL_NAME-$DJANGO_WL_VERSION.zip does not exist"
    exit 255
fi
if [ ! -f "$WORKING_DIR/$WEBTIER_PROV_NAME-$WEBTIER_PROV_VERSION.zip" ]; then
    echo "ERROR: $WORKING_DIR/$WEBTIER_PROV_NAME-$WEBTIER_PROV_VERSION.zip does not exist"
    exit 255
fi

rm -rf "$WORKING_DIR/$DJANGO_WL_INTERNAL_NAME-$DJANGO_WL_VERSION" "$WORKING_DIR/$DJANGO_WL_GENERIC_NAME"
unzip "$WORKING_DIR/$DJANGO_WL_INTERNAL_NAME-$DJANGO_WL_VERSION.zip"
mv "$WORKING_DIR/$DJANGO_WL_INTERNAL_NAME-$DJANGO_WL_VERSION" "$WORKING_DIR/$DJANGO_WL_GENERIC_NAME"
echo $DJANGO_WL_VERSION > "$WORKING_DIR/$DJANGO_WL_GENERIC_NAME/version"
cd "$WORKING_DIR"
rm -f "$DJANGO_WL_GENERIC_NAME.zip"
zip -r "$DJANGO_WL_GENERIC_NAME.zip" "$DJANGO_WL_GENERIC_NAME"

rm -rf "$WORKING_DIR/$WEBTIER_PROV_NAME-$WEBTIER_PROV_VERSION" "$WORKING_DIR/$WEBTIER_PROV_NAME"
unzip "$WORKING_DIR/$WEBTIER_PROV_NAME-$WEBTIER_PROV_VERSION.zip"
mv "$WORKING_DIR/$WEBTIER_PROV_NAME-$WEBTIER_PROV_VERSION" "$WORKING_DIR/$WEBTIER_PROV_NAME"
echo $WEBTIER_PROV_VERSION > "$WORKING_DIR/$WEBTIER_PROV_NAME/version"
mv "$WORKING_DIR/$DJANGO_WL_GENERIC_NAME.zip" "$WORKING_DIR/$WEBTIER_PROV_NAME/webtier/roles/django-uwsgi/files/"
cd "$WORKING_DIR/$WEBTIER_PROV_NAME/webtier"

ID_RSA_FILE=~/.ssh/id_rsa
SSH_CONFIG_FILE=~/.ssh/config
AUTH_KEYS_FILE=~/.ssh/authorized_keys
# generate ssh keys for localhost
if [ ! -f "$ID_RSA_FILE" ]; then
    yes y | ssh-keygen -t rsa -q -f "$ID_RSA_FILE" -N ''
fi
if [ -f "$SSH_CONFIG_FILE" ]; then
    mv "$SSH_CONFIG_FILE" "$SSH_CONFIG_FILE.django.old"
fi
echo "Host *" > "$SSH_CONFIG_FILE"
echo "   StrictHostKeyChecking no" >> "$SSH_CONFIG_FILE"
cat "$ID_RSA_FILE.pub" >> "$AUTH_KEYS_FILE"

# populate hosts file with target information
cat hosts | grep localhost
if [ $? -ne 0 ]; then
    sed -i "/^\[target\]/a localhost" hosts
fi
sed -i "s/^target_username=.*/target_username=$WHOAMI/g" hosts
sed -i "s/^base_dir=.*/base_dir=\"\/home\/{{target_username}}\/python-django\"/g" hosts
if [ -z "$http_proxy" ]; then
    sed -i "s/^set_internal_proxy=.*/set_internal_proxy=no/g" hosts
fi

# exit when any command fails
set -e

# install the django workload
ansible-playbook -i hosts django_workload.yml
rm -r "$WORKING_DIR/$DJANGO_WL_GENERIC_NAME"
if [ -f "$SSH_CONFIG_FILE.django.old" ]; then
    mv "$SSH_CONFIG_FILE.django.old" "$SSH_CONFIG_FILE"
fi
