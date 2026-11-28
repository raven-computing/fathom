#!/bin/bash
# Build the Fathom server Debian meta-package.
#
# All Debian package source files live in packaging/deb/. The build is run
# from a self-contained staging directory inside the build tree so that the
# source tree is never modified and all debhelper-generated files remain
# within the build directory.

set -euo pipefail;

USAGE="Usage: packaging/build.sh [--wheel-dir <PATH>]";

wheel_dir="build/dist";

while (( $# > 0 )); do
  case "$1" in
    --wheel-dir)
    if (( $# < 2 )); then
      echo "Missing value for --wheel-dir" >&2;
      exit 2;
    fi
    wheel_dir="$2";
    shift 2;
    ;;
    -\?|--help)
    echo "${USAGE}";
    exit 0;
    ;;
    *)
    echo "Unknown argument: '$1'" >&2;
    echo "${USAGE}" >&2;
    exit 2;
    ;;
  esac
done

if ! command -v dpkg-buildpackage >/dev/null 2>&1; then
  echo "Missing dpkg-buildpackage. Install the Debian development tools." >&2;
  exit 1;
fi

project_version="$(tr -d '[:space:]' < VERSION)";
wheel_version="${project_version/-dev/.dev0}";
debian_version="$(dpkg-parsechangelog --file packaging/deb/changelog -S Version)";
expected_debian_version="${project_version/-dev/~dev}";
if [ "${debian_version}" != "${expected_debian_version}" ]; then
  echo "packaging/deb/changelog version '${debian_version}' does not match " \
       "project version '${expected_debian_version}'." >&2;

  exit 1;
fi

base_wheel="${wheel_dir}/raven_fathom_base-${wheel_version}-py3-none-any.whl";
server_wheel="${wheel_dir}/raven_fathom_server-${wheel_version}-py3-none-any.whl";
for wheel in "${base_wheel}" "${server_wheel}"; do
  if [ ! -f "${wheel}" ]; then
    echo "Required Fathom wheel is missing: ${wheel}" >&2;
    echo "Build the Python distributions first with build.sh." >&2;
    exit 1;
  fi
done

# Prepare a fresh, fully self-contained staging directory.
#
# dpkg-buildpackage requires a 'debian/' subdirectory in its working
# directory, so we copy packaging/deb/ there.
#
# The debian/rules file and fathom-server.install reference paths of the
# form 'packaging/deb/<file>' relative to the working directory, so we
# reproduce that sub-path inside the staging directory as well. This keeps
# the rules and install files unchanged while isolating the build entirely
# within the build tree.
staging="build/deb/stage";
rm -rf "${staging}";
mkdir -p "${staging}";

cp -r packaging/deb "${staging}/debian";
mkdir -p "${staging}/packaging";
cp -r packaging/deb "${staging}/packaging/deb";

# Copy the wheels into the staging area and pass the path as an absolute
# path so it remains valid regardless of the working directory.
staging_wheels="${staging}/build/deb/wheels";
mkdir -p "${staging_wheels}";
cp "${base_wheel}" "${server_wheel}" "${staging_wheels}/";
abs_wheel_dir="$(readlink -f "${staging_wheels}")";

# Run the build from within the staging directory.
# dpkg-buildpackage places the resulting .deb, .buildinfo, and .changes in
# the parent directory of the working directory, i.e. build/deb/.
(
  cd "${staging}";
  FATHOM_DEBIAN_WHEEL_DIR="${abs_wheel_dir}" \
      dpkg-buildpackage --build=binary --unsigned-source --unsigned-changes;
)

mkdir -p build/dist;
deb_file="build/deb/fathom-server_${debian_version}_all.deb";
if [ ! -f "${deb_file}" ]; then
  echo "Expected package was not created: ${deb_file}" >&2;
  exit 1;
fi
for artifact_type in deb buildinfo changes; do
  artifact="build/deb/fathom-server_${debian_version}_all.${artifact_type}";
  if [ -f "${artifact}" ]; then
    mv "${artifact}" build/dist/;
  fi
done

echo "Debian package: build/dist/$(basename "${deb_file}")";
exit 0;
