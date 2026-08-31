#!/bin/bash
# Build script for the Fathom program.

USAGE="Usage: build.sh [options]";

HELP_TEXT=$(cat << EOS
Builds distribution packages for the Fathom application.

${USAGE}

Options:

  [--clean]         Remove the build data and related files and then exit.

  [--docs]          Build the documentation and then exit.

  [--isolated]      Execute the entire build process in an isolated Docker container.

  [--no-virtualenv] Do not use a virtual environment for the build.

  [--skip-tests]    Do not run unit tests.

  [--verbose]       Enable verbose output. This will show additional information on the screen.

  [-?|--help]       Show this help message.

EOS
)

# Arg flags
ARG_CLEAN=false;
ARG_DOCS=false;
ARG_ISOLATED=false;
ARG_NO_VIRTUALENV=false;
ARG_SKIP_TESTS=false;
ARG_VERBOSE=false;
ARG_SHOW_HELP=false;

# Array of arguments passed through to an isolated run.
# Should be set in arg-parse loop below.
ARGS_ISOLATED=();

# Parse all arguments given to this script
for arg in "$@"; do
  case $arg in
    --clean)
    ARG_CLEAN=true;
    shift
    ;;
    --docs)
    ARG_DOCS=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --isolated)
    ARG_ISOLATED=true;
    # When running in an isolated container,
    # we don't need additional virtual envs
    ARGS_ISOLATED+=(--no-virtualenv);
    shift
    ;;
    --no-virtualenv)
    ARG_NO_VIRTUALENV=true;
    shift
    ;;
    --skip-tests)
    ARG_SKIP_TESTS=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --verbose)
    ARG_VERBOSE=true;
    ARGS_ISOLATED+=($arg);
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
    echo "Run 'build.sh --help' for more information";
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

# Check clean flag
if [[ $ARG_CLEAN == true ]]; then
  if [ -d "build" ]; then
    rm -r "build";
  fi
  egg_info_dirs=(*.egg-info);
  for egg_info_dir in "${egg_info_dirs[@]}"; do
    if [ -d "$egg_info_dir" ]; then
      rm -r "$egg_info_dir";
    fi
  done
  logI "Removed build data";
  exit 0;
fi

if [[ $ARG_ISOLATED == true ]]; then
  source ".docker/controls.sh";
  project_run_isolated build "${ARGS_ISOLATED[@]}";
  exit $?;
fi

if [[ $ARG_NO_VIRTUALENV == false ]]; then
  # Setup and activate virtual environment.
  # Unless we are already running in an isolated container.
  if ! [ -f "/.dockerenv" ]; then
    if ! setup_virtual_env; then
      exit 1;
    fi
  fi
fi

if [[ $ARG_DOCS == true ]]; then
  if ! command -v "mkdocs" &> /dev/null; then
    logE "Could not find the 'mkdocs' executable.";
    logE "Please make sure that MkDocs is correctly installed";
    echo "or try with the '--isolated' option to build inside a Docker container.";
    exit 1;
  fi
  verbose_arg="";
  if [[ $ARG_VERBOSE == true ]]; then
    verbose_arg="--verbose";
  fi
  # See https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0
  export NO_MKDOCS_2_WARNING="1";
  logI "Building documentation";
  mkdocs build --config-file "docs/mkdocs.yaml" $verbose_arg;
  mkdocs_status=$?;
  if (( mkdocs_status != 0 )); then
    logE "Failed to build documentation";
    logE "MkDocs finished with exit status $mkdocs_status";
  else
    page_label="build/site/index.html";
    page_url="file://${PWD}/${page_label}";
    page_link="\e]8;;${page_url}\e\\\\${page_label}\e]8;;\e\\\\";
    logI "Documentation HTML page is available at ${page_link}";
  fi
  exit $mkdocs_status;
fi

# Check skip-tests flag
if [[ $ARG_SKIP_TESTS == false ]]; then
  # Execute the test script
  test_args=();
  if [[ $ARG_NO_VIRTUALENV == true ]]; then
    test_args+=("--no-virtualenv");
  fi
  if ! bash test.sh "${test_args[@]}"; then
    exit $?;
  fi
fi

quiet_arg="";
if [[ $ARG_VERBOSE == false ]]; then
  quiet_arg="--quiet";
fi

logI "Building base source and binary distribution packages";
# Instruct the build frontend to not use any additional isolation
# with venv for the build, since at this point we are already in
# the virtual environment of the project.
export FATHOM_BUILD_TARGET="base";
${_PYTHON_EXEC} -m build $quiet_arg --outdir "${_DIST_DIRECTORY}" --no-isolation;
if (( $? != 0 )); then
  logE "Failed to build base distribution packages";
  exit 1;
fi
logI "Building client source and binary distribution packages";
export FATHOM_BUILD_TARGET="client";
${_PYTHON_EXEC} -m build $quiet_arg --outdir "${_DIST_DIRECTORY}" --no-isolation;
if (( $? != 0 )); then
  logE "Failed to build client distribution packages";
  exit 1;
fi
logI "Building server source and binary distribution packages";
export FATHOM_BUILD_TARGET="server";
${_PYTHON_EXEC} -m build $quiet_arg --outdir "${_DIST_DIRECTORY}" --no-isolation;
if (( $? != 0 )); then
  logE "Failed to build server distribution packages";
  exit 1;
fi
logI "Build successful";
exit 0;
