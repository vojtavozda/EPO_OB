
# %%

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import patches

def str2sec(time_str:str):
    
    """ Convert string '+-HH:MM:SS' to seconds """

    if time_str == '': return np.nan

    try:
        time_str = time_str.replace('+','')
        sign = 1 if '-' not in time_str else -1
        time_str = time_str.replace('-','')
        h,m,s = time_str.split(':')
        # print(f'str2sec({time_str})',sign,h,m,s)
        return sign*(int(h)*3600 + int(m)*60 + int(s))
    except:
        return np.nan

def sec2str(seconds:int,add_sign=False):

    """ Convert seconds to string 'HH:MM:SS' """

    if np.isnan(seconds): return np.nan
    
    if seconds >= 0:
        if add_sign:
            sign = '+'
        else:
            sign = ''
    else:
        sign = '-'
    seconds = abs(seconds)

    m, s = divmod(seconds,60)
    h, m = divmod(m,60)
    return sign + '%02d:%02d:%02d'%(h,m,s)


df = pd.read_csv("/home/vovo/Programming/python/EPO_OB/data.csv",index_col='ID')
df['Start'] = df['Start'].apply(lambda x: str2sec(x))
df['Finish'] = df['Finish'].apply(lambda x: str2sec(x))
df['Time'] = df['Finish']-df['Start']
df = df.sort_values(by=['Score','Time'],ascending=[False,True])

start = df['Start'].to_numpy()
start = start[~np.isnan(start)].astype(int)
finish = df['Finish'].to_numpy()
finish = finish[~np.isnan(finish)].astype(int)

fig, ax1 = plt.subplots()
for i in range(len(start)):
    ax1.plot([start[i],finish[i]],[i,i],color='k')
locs = ax1.get_xticks()
locs = locs[::2]
ax1.set_xticks(locs)
ax1.set_xticklabels([sec2str(t) for t in locs])
ax1.set_xlabel('Time')
ax1.set_ylabel('Rank')

ax2 = ax1.twinx()

inForestX = np.sort(np.unique(np.concatenate((start,finish))))
inForestN = np.empty(len(inForestX))

for i in range(len(start)):
    i1 = np.where(inForestX == start[i])[0][0]
    i2 = np.where(inForestX == finish[i])[0][0]+1
    inForestN[i1:i2] += 1
ax2.step(inForestX,inForestN,linewidth=2)
ax2.set_ylabel('Number of people in forest')
plt.show()
# %%
