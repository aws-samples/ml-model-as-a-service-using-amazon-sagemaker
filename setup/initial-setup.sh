#!/bin/bash -e

# Check if NVM is installed
if command -v nvm >/dev/null 2>&1; then
  echo "NVM is already installed."
else
  echo "NVM is not installed. Installing NVM..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
  source /etc/bashrc
  #Close and reopen your terminal to start using nvm or run the following to use it now
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
  echo "NVM installed successfully."
fi

# Verify NVM installation
nvm --version

. $(echo ~)/.nvm/nvm.sh

# #Install python3.8
# sudo yum update -y
# sudo yum install -y amazon-linux-extras
# sudo amazon-linux-extras enable python3.8
# sudo yum install -y python3.8
# sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
# sudo alternatives --set python3 /usr/bin/python3.8

# Uninstall aws cli v1 and Install aws cli version-2.3.0
# sudo pip2 uninstall awscli -y
# python3 -m pip uninstall awscli -y

# echo "Installing aws cli version-2.3.0"
# curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-2.3.0.zip" -o "awscliv2.zip"
# unzip awscliv2.zip
# sudo ./aws/install --update
# rm awscliv2.zip
# rm -rf aws 

# Install sam cli version 1.64.0
echo "Installing sam cli version 1.64.0"
rm -rf sam-installation
wget https://github.com/aws/aws-sam-cli/releases/download/v1.64.0/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install --update
if [ $? -ne 0 ]; then
	echo "Sam cli is already present, so deleting existing version"
	sudo rm /usr/local/bin/sam
	sudo rm -rf /usr/local/aws-sam-cli
	echo "Now installing sam cli version 1.64.0"
	sudo ./sam-installation/install    
fi
rm aws-sam-cli-linux-x86_64.zip
rm -rf sam-installation

# Install git-remote-codecommit version 1.15.1
echo "Installing git-remote-codecommit version 1.15.1"
# curl -O https://bootstrap.pypa.io/get-pip.py
# python3 get-pip.py --user
# rm get-pip.py

python3 -m pip install git-remote-codecommit==1.15.1

# Install node v18.18.0
# echo "Installing node v18.18.0"
# nvm deactivate
# nvm uninstall node
# nvm install v18.18.0
# nvm use v18.18.0
# nvm alias default v18.18.0


# Install cdk cli latest version 2.x.x
echo "Installing cdk cli latest version 2.x.x"
npm uninstall -g aws-cdk
npm install -g aws-cdk@^2 --force

#Install jq version
sudo yum -y install jq

#Install pylint version 2.11.1
python3 -m pip install pylint==2.11.1

#Install python requirements
python3 -m pip install -r ../server/sm-pipeline-cdk/requirements.txt
 
echo "Script Completed successfully!"
