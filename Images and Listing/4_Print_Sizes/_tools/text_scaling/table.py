import pickle, os, io, numpy as np, cairosvg
from PIL import Image, ImageFilter
from lay import split, inside, TABLE
CR={'Bartram_Trail':(9353,6596,10226,6648),'Art_Loeb_Trail':(9522,6980,10395,7032),'Mountains_to_Sea_Trail':(9477,6486,10350,6538)}
def runs(intervals, lo, hi, merge):
    a=np.zeros(hi-lo+2,bool)
    for x0,x1 in intervals: a[int(x0)-lo:int(x1)-lo+1]=True
    out=[];i=0
    while i<len(a):
        if a[i]:
            j=i
            while j<len(a) and a[j]: j+=1
            if out and i-out[-1][1]<merge: out[-1][1]=j
            else: out.append([i,j])
            i=j
        else: i+=1
    return [(lo+x0,lo+x1) for x0,x1 in out]
def load(m):
    p=m+'.t.pkl'
    if os.path.exists(p): return pickle.load(open(p,'rb'))
    head,groups,cr=split(m); r=TABLE[m]
    tsubs=[(gi,d,bb) for gi,(a,subs) in enumerate(groups) for d,bb in subs if inside(bb,r)]
    cols=runs([(b[0],b[2]) for _,_,b in tsubs],0,11000,120)
    rows=runs([(b[1],b[3]) for _,_,b in tsubs],0,8000,20)
    cl={}
    for gi,d,b in tsubs:
        cx=(b[0]+b[2])/2; cy=(b[1]+b[3])/2
        c=next(i for i,(a,z) in enumerate(cols) if a-1<=cx<=z+1); rr=next(i for i,(a,z) in enumerate(rows) if a-1<=cy<=z+1)
        cl.setdefault((gi,c,rr),[]).append(d)
    rest=[(a,' '.join(d for d,bb in subs if not inside(bb,r))) for a,subs in groups]
    D=dict(head=head,attrs=[a for a,_ in groups],rest=rest,cl=cl,cols=cols,rows=rows,cr=cr)
    pickle.dump(D,open(p,'wb')); return D
def layout(D,f,g,lf,top):
    cols,rows=D['cols'],D['rows']; w=[z-a for a,z in cols]; Rr=cols[-1][1]; T=rows[0][0]
    L3n=Rr-w[2]*f; A2n=L3n-g-w[1]*f/2; R1n=A2n-w[1]*f/2-g
    A=[(cols[0][1],R1n),((cols[1][0]+cols[1][1])/2,A2n),(cols[2][0],L3n)]
    M={}
    nh=D.get('nh',1); Hb=rows[nh][0]   # first body row top
    for (gi,c,rr) in D['cl']:
        yc=(rows[rr][0]+rows[rr][1])/2
        if rr<nh: yn=top+(yc-T)*f
        else: yn=top+(Hb-T)*f+(yc-Hb)*f*lf
        tx=A[c][1]-f*A[c][0]; ty=yn-f*yc
        M[(gi,c,rr)]=(tx,ty)
    bbox=(R1n-w[0]*f, top, Rr, top+(rows[-1][1]-T)*f*lf)  # approx
    return M,bbox
def svg(m,D,f=1,g=None,lf=1,top=None,fc=1,cdy=0,cmap=None,parts=('rest','table','copy')):
    cols,rows=D['cols'],D['rows']
    if g is None: g=cols[1][0]-cols[0][1]
    if top is None: top=rows[0][0]
    M,_=layout(D,f,g,lf,top)
    A=lambda a: cmap(a) if cmap else a
    o=[D['head']]
    if 'rest' in parts:
        for a,d in D['rest']:
            if d: o.append(f'<g {A(a)}><path d="{d}"/></g>')
    if 'table' in parts:
        for k,ds in D['cl'].items():
            tx,ty=M[k]; o.append(f'<g transform="matrix({f},0,0,{f},{tx:.2f},{ty:.2f})"><g {A(D["attrs"][k[0]])}><path d="{" ".join(ds)}"/></g></g>')
    if 'copy' in parts:
        c=CR[m]; ca,cb=D['cr']
        o.append(f'<g transform="translate({c[2]},{c[1]+cdy}) scale({fc}) translate({-c[2]},{-c[1]})"><g {A(ca)}>{cb}</g></g>')
    o.append('</svg>'); return ''.join(o)
def render(s,w,h=None):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode(),output_width=int(w),output_height=None if h is None else int(h),background_color='white'))).convert('L')
S=4.0
def fit(m,D,f,g,lf,pad=70,copy_reserve=True):
    rest=render(svg(m,D,parts=('rest',)),10412/S); H=rest.height
    R=np.asarray(rest)<246
    if copy_reserve:
        c=CR[m]; R[int((c[1]-80)/S):int((c[3]+30)/S), int(7500/S):]=True
    Rp=np.asarray(Image.fromarray((R*255).astype('uint8')).filter(ImageFilter.MaxFilter(2*int(pad/S)+1)))>0
    T0=D['rows'][0][0]
    Tm=np.asarray(render(svg(m,D,f,g,lf,top=T0,parts=('table',)),10412/S,H))<246
    ys,xs=np.where(Tm); t0,t1=ys.min(),ys.max()+1; tab=Tm[t0:t1]
    best=None
    for top in range(0,H-(t1-t0)):
        if not (Rp[top:top+(t1-t0)]&tab).any():
            d=abs(top-t0)
            if best is None or d<best[1]: best=(top,d)
    return None if best is None else T0+(best[0]-t0)*S
import re as _re
EXTRA=1400
def grow(D):
    h=D['head']
    vb=_re.search(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"',h)
    H=float(vb.group(4)); D2=dict(D); D2['H0']=H
    h=h.replace(vb.group(0),f'viewBox="{vb.group(1)} {vb.group(2)} {vb.group(3)} {H+EXTRA}"')
    h=_re.sub(r'height="[\d.]+in"',f'height="{(H+EXTRA)/600:.4f}in"',h,1)
    D2['head']=h; D2['nh']=NH.get(D2.get('m'),1); return D2
NH={'Bartram_Trail':2,'Art_Loeb_Trail':1,'Mountains_to_Sea_Trail':1}
def fit2(m,D,f,g,lf,pad=150):
    """table may extend below; copyright is re-placed later. Returns top or None."""
    rest=render(svg(m,D,parts=('rest',)),10412/S); H=rest.height
    R=np.asarray(rest)<246
    Rp=np.asarray(Image.fromarray((R*255).astype('uint8')).filter(ImageFilter.MaxFilter(2*int(pad/S)+1)))>0
    T0=D['rows'][0][0]
    Tm=np.asarray(render(svg(m,D,f,g,lf,top=T0,parts=('table',)),10412/S,H))<246
    ys,xs=np.where(Tm); t0,t1=ys.min(),ys.max()+1; tab=Tm[t0:t1]
    best=None
    for top in range(0,H-(t1-t0)):
        if not (Rp[top:top+(t1-t0)]&tab).any():
            d=abs(top-t0)
            if best is None or d<best[1]: best=(top,d)
    return None if best is None else (T0+(best[0]-t0)*S, T0+(best[0]-t0)*S+(t1-t0)*S)
