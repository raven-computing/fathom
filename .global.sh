#!/bin/bash
# ---------------------------------------------------------------------------- #
#                  Global configuration values and functions                   #
# ---------------------------------------------------------------------------- #


# Virtual environment name
_VIRTENV_NAME="fathom";

# Python executable
_PYTHON_EXEC="python";

# PIP executable
_PIP_EXEC="pip";

# Name of the main lib Python package
_PROJECT_SRC_PACKAGE_MAIN="raven";

# The relative path to the directory where distribution
# packages are placed when building
_DIST_DIRECTORY="build/dist"

# Terminal colors
_RED="\033[0;31m";
_GREEN="\033[0;32m";
_BLUE="\033[1;34m";
_ORANGE="\033[1;33m";
_NC="\033[0m";


# Print info level statement on stdout
function logI() {
  if [[ "$TERMINAL_USE_ANSI_COLORS" == "0" ]]; then
    echo "[INFO] $*";
  else
    echo -e "[${_BLUE}INFO${_NC}] $*";
  fi
}

# Print warning level statement on stdout
function logW() {
  if [[ "$TERMINAL_USE_ANSI_COLORS" == "0" ]]; then
    echo "[WARN] $*";
  else
    echo -e "[${_ORANGE}WARN${_NC}] $*";
  fi
}

# Print error level statement on stdout
function logE() {
  if [[ "$TERMINAL_USE_ANSI_COLORS" == "0" ]]; then
    echo "[ERROR] $*";
  else
    echo -e "[${_RED}ERROR${_NC}] $*";
  fi
}

# Print debug level statement on stdout
function logD() {
  if [[ "$TERMINAL_USE_ANSI_COLORS" == "0" ]]; then
    echo "[DEBUG] $*";
  else
    echo -e "[${_BLUE}DEBUG${_NC}] $*";
  fi
}

# Print critical level statement on stdout
function log_critical() {
  if [[ "$TERMINAL_USE_ANSI_COLORS" == "0" ]]; then
    echo "[CRITICAL] $*";
  else
    echo -e "[${_RED}CRITICAL${_NC}] $*";
  fi
}

# Prints the content of the specified log file and
# colourises the log level blocks.
function show_log_file() {
  local arg_file="$1";
  local line="";
  local sep="";
  local i;
  for (( i=0; i<70; ++i )); do
      sep="${sep}-";
  done
  echo "$sep";
  while read -r line || [ -n "$line" ]; do
    if [[ "$line" == "[INFO] "* ]]; then
      logI "${line:7}";
    elif [[ "$line" == "[WARN] "* ]]; then
      logW "${line:7}";
    elif [[ "$line" == "[ERROR] "* ]]; then
      logE "${line:8}";
    elif [[ "$line" == "[DEBUG] "* ]]; then
      logD "${line:8}";
    elif [[ "$line" == "[CRITICAL] "* ]]; then
      log_critical "${line:11}";
    else
      echo "$line";
    fi
  done < "$arg_file"
  echo "$sep";
}
