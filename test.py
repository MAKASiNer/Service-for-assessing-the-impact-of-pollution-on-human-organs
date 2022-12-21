import numpy as np


a = np.asarray([None, None, None, 1, 2, None, None, 5, 6, None, None])


def recover(a):
    j = None
    for i, p in enumerate(a):
        if p is not None:
            if j is None:
                a[j: i] = np.ones(i) * p
            else:
                a[j: i] = np.linspace(a[j], p, i - j)
            j = i
    a[j: ] = np.ones(i - j + 1) * a[j]
        
            


recover(a)
print(a)