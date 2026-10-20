#!/usr/bin/env bash
export LANG=en_US.UTF-8
cd "$HOME/qgc"
exec ./QGroundControl-x86_64.AppImage "$@"
