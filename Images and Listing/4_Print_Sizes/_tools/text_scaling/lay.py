import re, io, numpy as np, cairosvg
from svgpathtools import parse_path, Path
from PIL import Image
TABLE={'Bartram_Trail':(7250,450,10350,3320),'Art_Loeb_Trail':(6200,550,9800,2500),'Mountains_to_Sea_Trail':(6600,3850,10150,6440)}
def to_vb(z): return z.real*0.1, 6872-z.imag*0.1
def split(m):
    """return svg text, list of groups: (attrs, [(subpath_d, bbox_vb)]) and copyright group raw"""
    s=open(m+'.svg').read()
    head=s[:s.index('<g ')]
    groups=[]; cr=None
    for g in re.finditer(r'<g ([^>]*)>(.*?)</g>',s,re.S):
        attrs,body=g.groups()
        if 'scale(0.1' not in attrs: cr=(attrs,body); continue
        d=re.search(r'd="([^"]*)"',body,re.S).group(1)
        P=parse_path(d); subs=[]
        for sp in P.continuous_subpaths():
            x0,x1,y0,y1=sp.bbox(); a=to_vb(complex(x0,y0)); b=to_vb(complex(x1,y1))
            subs.append((sp.d(), (min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))))
        groups.append((attrs,subs))
    return head, groups, cr
def inside(bb,r): cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2; return r[0]<=cx<=r[2] and r[1]<=cy<=r[3]
