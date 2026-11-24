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
SPLIT_HEADER={'Art_Loeb_Trail','Mountains_to_Sea_Trail'}
def split_header(tsubs):
    """Put the last column's one-line header (e.g. DAVIDSON RIVER) on two lines, left-aligned,
    matching the two-line first-column header (CAMP DANIEL / BOONE)."""
    from svgpathtools import parse_path
    cols=runs([(b[0],b[2]) for _,_,b in tsubs],0,11000,120)
    ytop=min(b[1] for _,_,b in tsubs)
    r0=runs([(b[1],b[3]) for _,_,b in tsubs],0,8000,20)[0]      # header row only
    hdr=lambda b: b[1]>=r0[0]-1 and b[3]<=r0[1]+1
    c0=[b for _,_,b in tsubs if hdr(b) and b[2]<=cols[0][1]+1]
    lines=runs([(b[1],b[3]) for b in c0],0,8000,5)          # header lines in column 1
    if len(lines)==1:                                        # one-line headers (MST): new line goes above,
        cap=lines[0][1]-lines[0][0]                          # second word stays on the header line
        lines=[(lines[0][0]-round(1.68*cap),lines[0][0]-round(0.68*cap)),lines[0]]   # Art Loeb header leading
    assert len(lines)==2, lines
    last=[i for i,(g,d,b) in enumerate(tsubs) if hdr(b) and b[0]>=cols[-1][0]-1]
    xs=runs([(tsubs[i][2][0],tsubs[i][2][2]) for i in last],0,11000,25)   # words
    w1=[i for i in last if tsubs[i][2][2]<=xs[0][1]+1]; w2=[i for i in last if i not in w1]
    left=xs[0][0]
    def move(i,dx,dy):
        g,d,b=tsubs[i]
        p=parse_path(d).translated(complex(dx*10,-dy*10))
        return (g,p.d(),(b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy))
    top1=min(tsubs[i][2][1] for i in w1); top2=min(tsubs[i][2][1] for i in w2)
    x2=min(tsubs[i][2][0] for i in w2)
    out=list(tsubs)
    for i in w1: out[i]=move(i,0,lines[0][0]-top1)
    for i in w2: out[i]=move(i,left-x2,lines[1][0]-top2)
    return out
STRIP_NUMBERS={'Mountains_to_Sea_Trail'}
TITLE_BLOCK={'Mountains_to_Sea_Trail':(6300,4900)}   # logo + title + subtitle: centers left of x / below y
def strip_numbers(tsubs):
    """Middle column rows read 'N · NAME': drop the number and the middle dot, re-center NAME."""
    from svgpathtools import parse_path
    cols=runs([(b[0],b[2]) for _,_,b in tsubs],0,11000,120)
    rows=runs([(b[1],b[3]) for _,_,b in tsubs],0,8000,20)
    c1=cols[1]; center=(c1[0]+c1[1])/2
    keep=[True]*len(tsubs); shift={}
    for r0,r1 in rows[1:]:                                    # body rows only
        idx=[i for i,(g,d,b) in enumerate(tsubs) if c1[0]-1<=(b[0]+b[2])/2<=c1[1]+1 and r0-1<=(b[1]+b[3])/2<=r1+1]
        hs=sorted(tsubs[i][2][3]-tsubs[i][2][1] for i in idx); cap=hs[len(hs)//2]
        def inside_other(i):
            b=tsubs[i][2]
            return any(j!=i and tsubs[j][2][0]<=b[0] and tsubs[j][2][2]>=b[2] and tsubs[j][2][1]<=b[1] and tsubs[j][2][3]>=b[3] for j in idx)
        def spaced(i):                                       # the separator has a word space on both sides
            b=tsubs[i][2]; others=[tsubs[j][2] for j in idx if j!=i]
            gl=min([b[0]-o[2] for o in others if o[2]<=b[0]+1]+[1e9]); gr=min([o[0]-b[2] for o in others if o[0]>=b[2]-1]+[1e9])
            return gl>cap*0.45 and gr>cap*0.45 and gl<1e9 and gr<1e9
        dots=[i for i in idx if (tsubs[i][2][3]-tsubs[i][2][1])<cap*0.4 and (tsubs[i][2][2]-tsubs[i][2][0])<cap*0.4
              and abs((tsubs[i][2][1]+tsubs[i][2][3])/2-(r0+r1)/2)<cap*0.35 and not inside_other(i) and spaced(i)]
        if not dots: continue                                   # e.g. last row has no number
        dot=min(dots,key=lambda i:tsubs[i][2][0])                # leftmost free-standing dot = the separator
        dx_dot=tsubs[dot][2][2]
        drop=[i for i in idx if tsubs[i][2][2]<=dx_dot+1]
        name=[i for i in idx if i not in drop]
        for i in drop: keep[i]=False
        nx0=min(tsubs[i][2][0] for i in name); nx1=max(tsubs[i][2][2] for i in name)
        dx=center-(nx0+nx1)/2
        for i in name: shift[i]=dx
    out=[]
    for i,(g,d,b) in enumerate(tsubs):
        if not keep[i]: continue
        if i in shift:
            dx=shift[i]; d=parse_path(d).translated(complex(dx*10,0)).d(); b=(b[0]+dx,b[1],b[2]+dx,b[3])
        out.append((g,d,b))
    return out
def load(m):
    p=m+'.t.pkl'
    if os.path.exists(p): return pickle.load(open(p,'rb'))
    head,groups,cr=split(m); r=TABLE[m]
    tsubs=[(gi,d,bb) for gi,(a,subs) in enumerate(groups) for d,bb in subs if inside(bb,r)]
    if m in SPLIT_HEADER: tsubs=split_header(tsubs)
    if m in STRIP_NUMBERS: tsubs=strip_numbers(tsubs)
    cols=runs([(b[0],b[2]) for _,_,b in tsubs],0,11000,120)
    rows=runs([(b[1],b[3]) for _,_,b in tsubs],0,8000,20)
    cl={}
    for gi,d,b in tsubs:
        cx=(b[0]+b[2])/2; cy=(b[1]+b[3])/2
        c=next(i for i,(a,z) in enumerate(cols) if a-1<=cx<=z+1); rr=next(i for i,(a,z) in enumerate(rows) if a-1<=cy<=z+1)
        cl.setdefault((gi,c,rr),[]).append(d)
    TB=TITLE_BLOCK.get(m)
    in_title=(lambda bb: TB is not None and (bb[0]+bb[2])/2<TB[0] and (bb[1]+bb[3])/2>TB[1])
    rest=[(a,' '.join(d for d,bb in subs if not inside(bb,r) and not in_title(bb))) for a,subs in groups]
    title=[(a,' '.join(d for d,bb in subs if not inside(bb,r) and in_title(bb))) for a,subs in groups]
    tbb=[bb for a,subs in groups for d,bb in subs if not inside(bb,r) and in_title(bb)]
    title_bottom=max(bb[3] for bb in tbb) if tbb else None
    D=dict(head=head,attrs=[a for a,_ in groups],rest=rest,cl=cl,cols=cols,rows=rows,cr=cr,title=title,title_bottom=title_bottom)
    pickle.dump(D,open(p,'wb')); return D
def layout(D,f,g,lf,top,Rr=None):
    cols,rows=D['cols'],D['rows']; w=[z-a for a,z in cols]; Rr=(D.get('Rr') or cols[-1][1]) if Rr is None else Rr; T=rows[0][0]
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
def svg(m,D,f=1,g=None,lf=1,top=None,fc=1,cdy=0,cmap=None,parts=('rest','table','copy'),Rr=None):
    cols,rows=D['cols'],D['rows']
    if g is None: g=cols[1][0]-cols[0][1]
    if top is None: top=rows[0][0]
    M,_=layout(D,f,g,lf,top,Rr)
    A=lambda a: cmap(a) if cmap else a
    o=[D['head']]
    if 'rest' in parts:
        for a,d in D['rest']:
            if d: o.append(f'<g {A(a)}><path d="{d}"/></g>')
        tdy=D.get('tdy',0)
        for a,d in D.get('title',[]):
            if d: o.append(f'<g transform="translate(0,{tdy:.2f})"><g {A(a)}><path d="{d}"/></g></g>')
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
NH={'Bartram_Trail':2,'Art_Loeb_Trail':1,'Mountains_to_Sea_Trail':2}
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
