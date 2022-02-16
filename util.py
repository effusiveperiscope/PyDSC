# Miscellaneous utility functions
from chardet import detect
import numpy as np

def get_encoding_type(fi):
    with open(fi, 'rb') as f:
        rawdata = f.read()
        return detect(rawdata)['encoding']

def print_summary_stats(arr, name=None):
    if name:
        print("Summary stats for ",name)
    print("Mean: ",np.mean(arr))
    print("STD: ",np.std(arr))

def si_intersect(m1, m2, b1, b2):
    x = (b2-b1)/(m1-m2)
    return np.array([x, m1*x+b1])
