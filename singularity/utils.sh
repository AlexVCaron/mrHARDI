#!/usr/bin/env bash

remove_if_exists () {
    if [ -d  "$1" ]
    then
        rm -rf "$1"
    fi
}

assert_installation_complete () {
    [ -f "$1/$2_complete.flag" ] && echo "true" || echo ""
}

ERR_VAR=""

error_exit () {
    echo $ERR_VAR
    echo -e "\e[30;41m!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo -e "\e[30;41m                      THERE WAS AN ERROR WHILE BUILDING                      "
    echo -e "\e[30;41m!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    exit 0 # This hack allow us to build the singularity whether there is an error or not. Please check your output or log to see if everything has built
}

get_version () {
    echo "$1" | sed -E 's/.*-([[:digit:]]+(\.[[:digit:]]+)+(\.[^-]+)*)-.*/\1/'
}
