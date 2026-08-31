#!/bin/bash
# Release script for the Fathom application.
# This will release the source and binary distributions to PyPI.

USAGE="Usage: release.sh [options]";

HELP_TEXT=$(cat << EOS
Handles release versions of the Fathom application.

${USAGE}

Options:

  [--bump-version] <IDENT>
                   Bump the project version, where <IDENT> is either 'M' for major,
                   'm' for minor or 'p' for patch. This option will result in the
                   project version being incremented at the corresponding level.
                   A Git commit for the version change is created.

  [--testpypi]     Upload the build artifacts to the TestPyPI package index
                   instead of the real index.

  [-?|--help]  Show this help message.
EOS
)

# Arg flags
ARG_BUMP_VERSION=false;
ARG_TESTPYPI=false;
ARG_SHOW_HELP=false;

# Arg helper vars
arg_check_optarg=false;
arg_optarg_key="";
arg_optarg_required="";
arg_opt_arg="";

# Parse all arguments given to this script
for arg in "$@"; do
  if [[ $arg_check_optarg == true ]]; then
    arg_check_optarg=false;
    if [[ "$arg" != -* ]]; then
      arg_opt_arg="$arg";
      arg_optarg_required="";
      shift;
      continue;
    fi
  fi
  if [ -n "$arg_optarg_required" ]; then
    echo "Missing required option argument '${arg_optarg_required}'";
    exit 1;
  fi
  case $arg in
    --bump-version)
    ARG_BUMP_VERSION=true;
    arg_check_optarg=true;
    arg_optarg_required="IDENT";
    shift
    ;;
    --testpypi)
    ARG_TESTPYPI=true;
    shift
    ;;
    -\?|--help)
    ARG_SHOW_HELP=true;
    shift
    ;;
    *)
    # Unknown Argument
    echo "Unknown argument: '$arg'";
    echo "$USAGE";
    echo "";
    echo "Run 'deploy.sh --help' for more information";
    exit 1;
    ;;
  esac
done

# Check if help is triggered
if [[ $ARG_SHOW_HELP == true ]]; then
  echo "$HELP_TEXT";
  exit 0;
fi

# Source setup script
SETUPSH_VIRTUALENV_AUTO_ACTIVATE="0";
if ! source "setup.sh"; then
  exit 1;
fi

readonly FILE_VERSION="VERSION";
IS_DEV_VERSION=false;

function read_version() {
  if [ -r "$FILE_VERSION" ]; then
    VERSION=$(head -n 1 "$FILE_VERSION");
    VERSION_BASE="${VERSION%%-*}";
  fi
  local version_re="^[0-9]+\.[0-9]+\.[0-9]+(-dev)?$";
  if ! [[ $VERSION =~ $version_re ]]; then
    logW "Version specified in file '${FILE_VERSION}' has an invalid format. Abort.";
    exit 1;
  fi
  IS_DEV_VERSION=false;
  if [[ "$VERSION" == *-dev ]]; then
    IS_DEV_VERSION=true;
  fi
}

function update_version() {
  local version_change_index="$1";
  local version_array=( ${VERSION_BASE//./ } );
  local version_major="${version_array[0]}";
  local version_minor="${version_array[1]}";
  local version_patch="${version_array[2]}";
  if [ -n "$version_change_index" ]; then
    local version_new_value=$(( ${version_array[$version_change_index]} + 1 ));
    version_array[version_change_index]="$version_new_value";
    while (( version_change_index < 2 )); do
      ((++version_change_index));
      version_array[version_change_index]="0";
    done
  fi
  local new_version="${version_array[0]}.${version_array[1]}.${version_array[2]}";
  local new_version_base="$new_version";
  if [[ $IS_DEV_VERSION == true ]]; then
    new_version="${new_version}-dev";
  fi
  NEW_VERSION="$new_version";
  NEW_VERSION_BASE="$new_version_base";
}

function write_version() {
  echo -n "$NEW_VERSION" > "$FILE_VERSION";
}

function bump_version() {
  local ident="$1";
  local version_ident_index="";
  if [[ "$ident" == "M" ]]; then
    version_ident_index=0;
  elif [[ "$ident" == "m" ]]; then
    version_ident_index=1;
  elif [[ "$ident" == "p" ]]; then
    version_ident_index=2;
  else
    logE "Argument for option '--bump-version' must be one of ('M', 'm', 'p')";
    exit 1;
  fi
  read_version;
  update_version $version_ident_index;
  logI "Bumping current version ${VERSION}";
  write_version;
  logI "The new version is ${NEW_VERSION}";
  logI "Committing version change";
  git add . && git commit -m "Bump version" --no-signoff;
  if (( $? != 0 )); then
    logE "Failed to commit changes";
    exit 1;
  fi
}

if [[ $ARG_BUMP_VERSION == true ]]; then
  if [ -z "$arg_opt_arg" ]; then
    logE "Missing required option argument '${arg_optarg_required}'";
    exit 1;
  fi
  bump_version "$arg_opt_arg";
  exit 0;
fi

# Dependencies
if ! command -v "twine" &> /dev/null; then
  logE "Could not find requirement 'twine'";
  exit 1;
fi

# Build and test
if ! bash build.sh; then
  exit $?;
fi

logI "Running distribution checks";
twine check "${_DIST_DIRECTORY}"/*;
if (( $? != 0 )); then
  logE "Distribution checks have failed";
  exit 1;
fi
logI "All distribution checks have passed";

if [[ $ARG_TESTPYPI == true ]]; then
  logI "Uploading distributions to TestPyPI";
  twine upload --repository testpypi "${_DIST_DIRECTORY}"/*;
  if (( $? != 0 )); then
    logE "Failed to upload distributions";
    exit 1;
  fi
else
  logI "Uploading distributions to PyPI";
  twine upload "${_DIST_DIRECTORY}"/*;
  if (( $? != 0 )); then
    logE "Failed to upload distributions";
    exit 1;
  fi
fi
logI "Distributions have been successfully uploaded";
exit 0;
