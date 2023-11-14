
"""
In order to release new version, run `relase_app.sh` script.
"""

# %% ===========================================================================

print("Refreshing app files...")

import os
import sys
import shutil
import json
os.chdir('/home/vovo/Programming/python')

# Update app information -------------------------------------------------------
stngs_base_filepath = os.path.join("EPO_OB","app_fbs","src","build","settings","base.json")
with open(stngs_base_filepath,'r') as fh:
    json_base = json.load(fh)
# Main information
json_base['app_name'] = 'epoob'
json_base['author'] = 'vovo'
# Update version number
version = json_base['version'].split('.')
version[2] = str(int(version[2])+1)
json_base['version'] = version[0]+'.'+version[1]+'.'+version[2]
print(f"New version: {json_base['version']}")
# Save changes
with open(stngs_base_filepath,'w') as fh:
    json.dump(json_base,fh,indent=4)

# Copy files -------------------------------------------------------------------

shutil.copy2(
    os.path.join(stngs_base_filepath),
    os.path.join("EPO_OB","app_fbs","src","main","resources","base")
)

shutil.copy2(
    os.path.join("EPO_OB","test_event.csv"),
    os.path.join("EPO_OB","app_fbs","src","main","resources","base")
)

shutil.copy2(
    os.path.join("EPO_OB","epo_ob.py"),
    os.path.join("EPO_OB","app_fbs","src","main","python")
)

print("Done!")