
# %%

import pandas as pd
from enum import IntEnum, unique

@unique
class cols(IntEnum):
    id = 0
    name = 1
    gender = 2
    start = 3


aaa = ['zero','one','two','three']

print(aaa[cols.id])

# %%

df = pd.read_csv("/home/vovo/Programming/python/EPO_OB/data.csv",index_col='ID')
