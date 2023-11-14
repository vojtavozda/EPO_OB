#!/bin/bash

# while getops ":v" option; do
#     case $option in
#         v)


start=`date +%s`
BIGreen='\033[1;92m'
BIYellow='\033[1;93m'
NC='\033[0m'

echo_title() {
    echo -e "\n${BIYellow}=====[ $1 ]=====${NC}"
}

echo_done() {
    echo -e "${BIGreen}Done!${NC}"
}

echo_title "Update sudo"
sudo -v

echo -n "Activate virtual environment... "
source /home/vovo/Programming/python/.venv/bin/activate
echo_done

echo -n "Change to project directory... "
cd /home/vovo/Programming/python/EPO_OB/app_fbs
echo_done

echo_title "Run python script to refresh app"
python3 refresh_app.py

echo_title "fbs: Freeze"
fbs freeze

echo_title "fbs: Installer"
fbs installer

echo_title "Install package"
sudo dpkg -i target/epoob.deb

end=`date +%s`
echo -e "\nBuilding time: `expr $end - $start` seconds."

echo_title "Run app"
/opt/epoob/epoob