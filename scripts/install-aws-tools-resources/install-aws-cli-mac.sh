#!/bin/bash

set -Eeuo pipefail

# Check if directory argument is provided
if [ $# -ne 2 ]; then
  echo "Usage: $0 <history_directory> <install_parent_directory>" >&2
  exit 1
fi

echo "ensure directories exist: '$1' '$2'"
mkdir -p "$1" "$2"

history_dir="$(/usr/bin/readlink -f $1)"
install_parent_dir="$(/usr/bin/readlink -f $2)"

echo "history: $history_dir"
echo "target: $install_parent_dir"

pkg_file="$history_dir/AWSCLIV2.pkg"
xml_file="$history_dir/aws_cli_install.xml"

# Download the AWS CLI installation bundle
if [[ ! -f "$pkg_file" ]]; then
  echo "Downloading AWS CLI..."
  /usr/bin/curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "$pkg_file"
else
  echo "Using $pkg_file"
fi

# Generate custom XML file for installation
/usr/bin/m4 -D INSTALL_PARENT_DIR="$install_parent_dir" > "$xml_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <array>
    <dict>
      <key>choiceAttribute</key>
      <string>customLocation</string>
      <key>attributeSetting</key>
      <string>INSTALL_PARENT_DIR</string>
      <key>choiceIdentifier</key>
      <string>default</string>
    </dict>
  </array>
</plist>
EOF

/bin/mkdir -p "$install_parent_dir"

# Install AWS CLI using the custom XML file
echo "Installing AWS CLI..."
/usr/sbin/installer -pkg "$pkg_file" \
  -target CurrentUserHomeDirectory \
  -applyChoiceChangesXML "$xml_file"

"$install_parent_dir"/aws-cli/aws --version/aws-cli/aws --version

echo "AWS CLI version 2 installed successfully into:"
echo "$install_parent_dir"/aws-cli/aws
