import sys
import types

def get_refcounts():
    d = {}
    sys.modules
    # collect all classes
    for m in list(sys.modules.values()):
        for sym in dir(m):
            o = getattr (m, sym)
            if type(o) is type:
                d[o] = sys.getrefcount (o)
    # sort by refcount
    pairs = [(x[1],x[0]) for x in list(d.items())]
    pairs.sort()
    pairs.reverse()
    return pairs

#def print_top_100():
for n, c in get_refcounts()[:100]:
        print('%10d %s' % (n, c.__name__))

#print_top_100()
