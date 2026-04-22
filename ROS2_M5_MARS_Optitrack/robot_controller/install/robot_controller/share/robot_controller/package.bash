# generated from colcon_bash/shell/template/package.bash.em

# This scripts extends the environment for this package.

# a bash scripts is able to determine its own path if necessary
if [ -z "$COLCON_CURRENT_PREFIX" ]; then
  # the prefix is two levels up from the package specific share directory
  _colcon_package_bash_COLCON_CURRENT_PREFIX="$(builtin cd "`dirname "${BASH_SOURCE[0]}"`/../.." > /dev/null && pwd)"
else
  _colcon_package_bash_COLCON_CURRENT_PREFIX="$COLCON_CURRENT_PREFIX"
fi

# function to source another scripts with conditional trace output
# first argument: the path of the scripts
# additional arguments: arguments to the scripts
_colcon_package_bash_source_script() {
  if [ -f "$1" ]; then
    if [ -n "$COLCON_TRACE" ]; then
      echo "# . \"$1\""
    fi
    . "$@"
  else
    echo "not found: \"$1\"" 1>&2
  fi
}

# source sh scripts of this package
_colcon_package_bash_source_script "$_colcon_package_bash_COLCON_CURRENT_PREFIX/share/robot_controller/package.sh"

unset _colcon_package_bash_source_script
unset _colcon_package_bash_COLCON_CURRENT_PREFIX
