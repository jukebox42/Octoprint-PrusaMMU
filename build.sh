#!usr/bin/env bash

# bash build.sh YYYY.M.D

FILE="alpha.txt";

echo "=== Building PrusaMMU ===";
echo "";

# Set a base version if no version is provided
dt=`date +"%y.%-m.%-d"alpha`;

# Handle alpha versioning so it increments
alphaV=0;
if [ -z "$1" ]; then
  if [ -f "$FILE" ]; then
    alphaV=$(cat $FILE);
    alphaV=$(($alphaV + 1))
    echo "$alphaV" > "$FILE";
  else
    echo $(($alphaV)) > "$FILE";
  fi
  dt="$dt$alphaV";
else
  rm -f "$FILE";
fi

# Take inputs
echo "Settings:";
version="${1:-$dt}";
echo "- Version: $version";
echo "";


# Delete and recreate the build directory
rm -rf Octoprint-PrusaMmu
rm -f Octoprint-PrusaMmu.zip
mkdir Octoprint-PrusaMmu

# Copy files ans folders we need in the build
cp -r extras Octoprint-PrusaMmu/extras # this is empty so copy wont move it
cp -r octoprint_prusammu Octoprint-PrusaMmu/octoprint_prusammu
cp -r translations Octoprint-PrusaMmu/translations
cp babel.cfg Octoprint-PrusaMmu/babel.cfg
cp LICENSE.txt Octoprint-PrusaMmu/LICENSE.txt
cp MANIFEST.in Octoprint-PrusaMmu/MANIFEST.in
cp requirements.txt Octoprint-PrusaMmu/requirements.txt
cp setup.py Octoprint-PrusaMmu/setup.py

# Rewrite version
echo -n "Writing plugin version... "
sed -i "s/plugin_version = \"VERSION\"/plugin_version = \"$version\"/" Octoprint-PrusaMmu/setup.py
echo "done"

# Compress the build directory
echo -n "Zipping... ";
zip -q -r Octoprint-PrusaMmu.zip Octoprint-PrusaMmu
rm -rf Octoprint-PrusaMmu
echo "done";

echo "Done.";