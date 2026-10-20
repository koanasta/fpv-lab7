#!/bin/bash
export GZ_VERSION=harmonic
GZ_PLUGIN_DIR=$HOME/ardu_ws/install/ardupilot_gazebo/lib/ardupilot_gazebo
GZ_SHARE_DIR=$HOME/ardu_ws/install/ardupilot_gazebo/share/ardupilot_gazebo
export GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_PLUGIN_DIR:$GZ_SIM_SYSTEM_PLUGIN_PATH
export GZ_SIM_RESOURCE_PATH=$GZ_SHARE_DIR/..:$GZ_SHARE_DIR/models:$GZ_SHARE_DIR/worlds:$GZ_SIM_RESOURCE_PATH
export ARDUPILOT_DIR=$HOME/ardupilot-4.6
source $HOME/venv-ardupilot/bin/activate
export PATH=$ARDUPILOT_DIR/Tools/autotest:$PATH
