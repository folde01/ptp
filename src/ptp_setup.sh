#!/usr/bin/env bash

PROJ_HOME=$HOME/0proj/repo

# disable ipv6
if [ `cat /proc/sys/net/ipv6/conf/all/disable_ipv6` == 0 ]; 
then 
	sudo bash -c "echo 'net.ipv6.conf.all.disable_ipv6 = 1' >> /etc/sysctl.conf"
	sudo bash -c "echo 'net.ipv6.conf.default.disable_ipv6 = 1' >> /etc/sysctl.conf"
	sudo bash -c "echo 'net.ipv6.conf.lo.disable_ipv6 = 1' >> /etc/sysctl.conf"
	sudo sysctl -p
fi

# OS updates: 
sudo apt-get update
sudo apt-get -y dist-upgrade

# Dependencies: VPN (pptpd to start with), ntp, virtualenv, python 2, pip, scapy, libnids, pynids, flask, mock ...

sudo apt-get install mysql-server -y
sudo apt-get install pptpd -y
sudo apt-get -y install ntp
# todo: finish pptpd

sudo apt-get -y install libnet1-dev

# reboot if required

if [ -f /var/run/reboot-required ]; then
      echo 'Reboot required. Rerun this script after the VM has rebooted.'
      reboot
fi

#PTP_HOME=$HOME/ptp


PTP_HOME=$PROJ_HOME
PTP_PREREQS=$PTP_HOME/bbk-project/prereqs
mkdir -p $PTP_PREREQS

# make sure we're in virtualenv!


sudo apt-get install -y libmysqlclient-dev python-dev
python -m pip install flask scapy psutil netifaces mysqlclient

# For development only (in place of python repl):
# needs python 2.7.11 (which is why we use anaconda on 14.04, which has only 2.7.6)
python -m pip install jupyter 

# then follow this to run the jupyter notebook as a server on VM and make accessible remotely from host browser: http://jupyter-notebook.readthedocs.io/en/stable/public_server.html
#(venv) jo@ubuntu:~/ptp/PTP/src$ jupyter notebook --generate-config
#(venv) jo@ubuntu:~/ptp/PTP/src$ vim ~/.jupyter/jupyter_notebook_config.py
#(venv) jo@ubuntu:~/ptp/PTP/src$ grep c.NotebookApp.ip ~/.jupyter/jupyter_notebook_config.py
##c.NotebookApp.ip = 'localhost'
#c.NotebookApp.ip = '*'
#(venv) jo@ubuntu:~/ptp/PTP/src$ grep c.NotebookApp.open_browser ~/.jupyter/jupyter_notebook_config.py
##c.NotebookApp.open_browser = True
#c.NotebookApp.open_browser = False

mkdir -p $PTP_PREREQS

sudo apt-get -y install libpcap-dev pkg-config libglib2.0-dev

cd $PTP_PREREQS

#git clone https://github.com/MITRECND/pynids.git
#cd pynids
#python setup.py build
#python setup.py install

cd $PTP_PREREQS
git clone https://github.com/CoreSecurity/pcapy.git
cd pcapy
python setup.py install

# initialise db
cd $PTP_HOME/PTP/src
python ptp_init.py

./ptp_start.sh
