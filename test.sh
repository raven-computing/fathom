#!/bin/bash
# Test script for the Fathom program.

USAGE="Usage: test.sh [options] [--interactive <PROG> [args...]]";

HELP_TEXT=$(cat << EOS
Tests the Fathom application.

${USAGE}

Options:

  [--all]              Execute the entire test suite, with all checks and tests for all components.

  [--base]             Only consider the base package.

  [--client]           Only consider the client package.

  [--coverage]         Measure and report code coverage metrics for the test runs.

  [--filter]           <PATTERN>
                       Only execute tests that match the specified pattern.
                       The pattern can be a single module, module and class, or specifically a
                       single test method of a specific test class within a specific test module.
                       For example: 'test_module.TestClass.test_method'

  [-f|--functionality] Execute functionality tests.

  [-i|--integration]   Execute integration tests.

  [--interactive]      <PROG> [args...]
                       Starts either the client or server application for interactive testing.
                       The <PROG> options argument is mandatory and must either
                       be 'client' or 'server'. All optional arguments from [args...] are passed
                       to the invoked application as is. If specified, this must be the last given
                       option as all subsequent arguments will be interpreted as being part
                       of the [args...] option argument.

  [--isolated]         Execute the entire test process in an isolated Docker container.

  [-l|--lint]          Perform static code analysis with a linter.

  [--no-virtualenv]    Do not use a virtual environment for the tests.

  [--server]           Only consider the server package.

  [-t|--types]         Perform static code analysis with a type checker.

  [-u|--unit]          Execute unit tests.

  [-?|--help]          Show this help message.

EOS
)

# Arg flags
ARG_ALL=false;
ARG_BASE=false;
ARG_CLIENT=false;
ARG_COVERAGE=false;
ARG_FILTER=false;
ARG_FUNCTIONALITY=false;
ARG_INTEGRATION=false;
ARG_INTERACTIVE=false;
ARG_ISOLATED=false;
ARG_LINT=false;
ARG_NO_VIRTUALENV=false;
ARG_SERVER=false;
ARG_TYPES=false;
ARG_UNIT=false;
ARG_SHOW_HELP=false;

# Array of arguments passed through to an isolated run.
# Should be set in arg-parse loop below.
ARGS_ISOLATED=();

filter_opt_arg="";
app_prog="";
app_args=();

# Parse all arguments given to this script
for arg in "$@"; do
  if [[ $ARG_INTERACTIVE == true ]]; then
    if [ -z "$app_prog" ]; then
      app_prog="$arg";
    else
      app_args+=("$arg");
    fi
    ARGS_ISOLATED+=($arg);
    continue;
  fi
  if [[ $ARG_FILTER == true ]]; then
    if [ -z "$filter_opt_arg" ]; then
      filter_opt_arg="$arg";
      ARGS_ISOLATED+=($arg);
      continue;
    fi
  fi
  case $arg in
    --all)
    ARG_ALL=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --base)
    ARG_BASE=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --client)
    ARG_CLIENT=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --coverage)
    ARG_COVERAGE=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --filter)
    ARG_FILTER=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    -f|--functionality)
    ARG_FUNCTIONALITY=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    -i|--integration)
    ARG_INTEGRATION=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --interactive)
    ARG_INTERACTIVE=true;
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
    -l|--lint)
    ARG_LINT=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    --no-virtualenv)
    ARG_NO_VIRTUALENV=true;
    shift
    ;;
    --server)
    ARG_SERVER=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    -t|--types)
    ARG_TYPES=true;
    ARGS_ISOLATED+=($arg);
    shift
    ;;
    -u|--unit)
    ARG_UNIT=true;
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
    echo "Run 'test.sh --help' for more information";
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

if [[ $ARG_FILTER == true ]]; then
  if [ -z "$filter_opt_arg" ]; then
    logE "Missing argument <PATTERN> for --filter option";
    exit 1;
  fi
fi

# Check component flags
run_all=false;
if [[ $ARG_BASE == false && $ARG_CLIENT == false && $ARG_SERVER == false ]]; then
  ARG_BASE=true;
  ARG_CLIENT=true;
  ARG_SERVER=true;
  run_all=true;
fi
if [[ $ARG_ALL == true ]]; then
  ARG_BASE=true;
  ARG_CLIENT=true;
  ARG_SERVER=true;
  run_all=true;
  ARG_TYPES=true;
  ARG_LINT=true;
  ARG_UNIT=true;
  ARG_INTEGRATION=true;
  ARG_FUNCTIONALITY=true;
fi

if [[ $ARG_INTERACTIVE == true ]]; then
  if [[ "$app_prog" != "client" && "$app_prog" != "server" ]]; then
    logE "First option argument to --interactive option must either be 'client' or 'server'";
    exit 1;
  fi
fi

if [[ $ARG_ISOLATED == true ]]; then
  source ".docker/controls.sh";
  project_run_isolated_tests "${ARGS_ISOLATED[@]}";
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

if [[ $ARG_INTERACTIVE == true && $ARG_COVERAGE == true ]]; then
  logW "Cannot measure test coverage when testing interactively";
  ARG_COVERAGE=false;
fi

if [[ $ARG_INTERACTIVE == true ]]; then
  python -m raven.fathom.${app_prog} "${app_args[@]}";
  exit $?;
fi

if [[ $ARG_TYPES == true ]]; then
  if ! command -v "pyright" &> /dev/null; then
    logE "Could not find requirement 'pyright'";
    exit 1;
  fi
  logI "Performing static type checking";
  type_checker_output="$(FORCE_COLOR=1 pyright --warnings --threads)";
  type_checker_status=$?;
  if (( type_checker_status != 0 )); then
    echo "$type_checker_output";
    exit $type_checker_status;
  fi
  logI "Type checking completed without issues";
fi

if [[ $ARG_LINT == true ]]; then
  if ! command -v "pylint" &> /dev/null; then
    logE "Could not find requirement 'pylint'";
    exit 1;
  fi
  lint_status=0;
  if [[ $ARG_BASE == true ]]; then
    logI "Performing static code analysis of the base component";
    pylint --source-roots "$PWD" --ignore client,server "${_PROJECT_SRC_PACKAGE_MAIN}";
    lint_status=$?;
  fi
  if [[ $ARG_CLIENT == true ]]; then
    logI "Performing static code analysis of the client component";
    pylint --source-roots "$PWD" --ignore base,server "${_PROJECT_SRC_PACKAGE_MAIN}";
    next_lint_status=$?;
    if (( $lint_status == 0 )); then
      lint_status=$next_lint_status;
    fi
  fi
  if [[ $ARG_SERVER == true ]]; then
    logI "Performing static code analysis of the server component";
    pylint --source-roots "$PWD" --ignore base,client "${_PROJECT_SRC_PACKAGE_MAIN}";
    next_lint_status=$?;
    if (( $lint_status == 0 )); then
      lint_status=$next_lint_status;
    fi
  fi
  if [[ $run_all == true ]]; then
    logI "Performing static code analysis of the test suite";
    pylint --source-roots "$PWD" --disable duplicate-code "tests";
    next_lint_status=$?;
    if (( $lint_status == 0 )); then
      lint_status=$next_lint_status;
    fi
  fi
  if (( $lint_status == 0 )); then
    logI "No issues found in source files";
  else
    exit $lint_status;
  fi
fi

unit_test_filter="";
unit_test_filter_msg="";
if [[ $run_all == false ]]; then
  if [[ $ARG_BASE == true ]]; then
    unit_test_filter="/base";
    unit_test_filter_msg=" for the base component";
    if [[ $ARG_CLIENT == true ]]; then
      logW "Cannot use both --base and --client options";
      logW "Ignoring --client option";
    fi
    if [[ $ARG_SERVER == true ]]; then
      logW "Cannot use both --base and --server options";
      logW "Ignoring --server option";
    fi
  elif [[ $ARG_CLIENT == true ]]; then
    unit_test_filter="/client";
    unit_test_filter_msg=" for the client component";
    if [[ $ARG_SERVER == true ]]; then
      logW "Cannot use both --client and --server options";
      logW "Ignoring --server option";
    fi
  elif [[ $ARG_SERVER == true ]]; then
    unit_test_filter="/server";
    unit_test_filter_msg=" for the server component";
  fi
fi

if [[ $ARG_UNIT == false && $ARG_INTEGRATION == false && $ARG_FUNCTIONALITY == false ]]; then
  if [[ $ARG_TYPES == false && $ARG_LINT == false ]]; then
    ARG_UNIT=true;
  fi
fi

TEST_RUNNER_EXEC="${_PYTHON_EXEC}";
if [[ $ARG_COVERAGE == true ]]; then
  if ! command -v "coverage" &> /dev/null; then
    logE "Could not find requirement 'coverage'";
    exit 1;
  fi
  TEST_RUNNER_EXEC="coverage run";
fi

test_run_filter_arg="";
if [[ $ARG_FILTER == true ]]; then
  test_run_filter_arg="-k $filter_opt_arg"
fi

if [[ $ARG_UNIT == true ]]; then
  logI "Running unit tests${unit_test_filter_msg}";
  ${TEST_RUNNER_EXEC} -m unittest discover \
                      --start-directory "tests/unit${unit_test_filter}" \
                      --top-level-directory "." \
                      $test_run_filter_arg;

  if (( $? != 0 )); then
    logE "Tests have failed";
    exit 1;
  fi
  logI "All unit tests have passed";
fi

if [[ $ARG_INTEGRATION == true ]]; then
  logI "Running integration tests";
  export PYTHONPATH="${PWD}/tests";
  ${TEST_RUNNER_EXEC} -m unittest discover -s tests/integration $test_run_filter_arg;
  if (( $? != 0 )); then
    logE "Integration tests have failed";
    exit 1;
  fi
  logI "All integration tests have passed";
fi

if [[ $ARG_FUNCTIONALITY == true ]]; then
  logI "Running functionality tests";
  export PYTHONPATH="${PWD}/tests";
  ${TEST_RUNNER_EXEC} -m unittest discover \
                      --failfast \
                      --start-directory tests/functionality \
                      $test_run_filter_arg;

  if (( $? != 0 )); then
    server_logs="build/testing/server/logs";
    client_logs="build/testing/user/.local/state/fathom/client.log";
    echo;
    if [ -d "$server_logs" ]; then
      logI "Check server logs at ${server_logs}";
    else
      logI "No server logs available";
    fi
    if [ -f "$client_logs" ]; then
      logI "Client logs:";
      show_log_file "$client_logs";
      echo;
    else
      logI "No client logs available";
    fi
    logE "Functionality tests have failed";
    exit 1;
  fi
  logI "All functionality tests have passed";
fi

if [[ $ARG_COVERAGE == true ]]; then
  logI "Combining coverage data";
  coverage combine build/;
  if (( $? != 0 )); then
    logE "Failed to combine test coverage data";
    exit 1;
  fi
  logI "Generating test coverage report";
  coverage html --title="Fathom Test Coverage"
  if (( $? != 0 )); then
    logE "Failed to generate test coverage report";
    exit 1;
  fi
fi

exit 0;
