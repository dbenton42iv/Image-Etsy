from table import *
import json
G,LF=240,0.85
BASE={'Bartram_Trail':(66,48,70),'Art_Loeb_Trail':(78,48,66),'Mountains_to_Sea_Trail':(58,48,56)}  # cap heights (units): table, copyright, labels
FILES=[('7x5',7,5,.125,5,7),('14x11',14,11,.10,11,14),('20x16',20,16,.125,8,10),('24x18',24,18,.10,6,8),('36x24',36,24,.125,8,12),('A1_landscape',33.11,23.39,.10,5.83,8.27)]
# 20x16 / 36x24 files: text sized for 8x10 / 8x12 (4x5 and 4x6 are too small for a mileage table either way)
def compose(m,D,f,fc):
    if f==1.0: top=D['rows'][0][0]; bot=None
    else:
        t=fit2(m,D,f,G,LF)
        if t is None: return None
        top=t[0]
    s_rest=svg(m,D,parts=('rest',)); R=np.asarray(render(s_rest,10412/S))<246
    ys,xs=np.where(R); rest_bot=ys.max()*S
    gl,glf=(G,LF) if f!=1.0 else (None,1)
    Tm=np.asarray(render(svg(m,D,f,gl,glf,top=top,parts=('table',)),10412/S))<246
    ty,tx=np.where(Tm); tab_bot=ty.max()*S
    c=CR[m]; ob=max(rest_bot, D['rows'][-1][1]); gap0=max(70, c[1]-ob)
    cy=max(rest_bot,tab_bot)+gap0      # new copyright top
    full=svg(m,D,f,gl,glf,top=top,fc=fc,cdy=cy-c[1])
    A=np.asarray(render(full,10412/S))<246; ay,ax=np.where(A)
    return dict(f=f,fc=fc,top=top,cdy=cy-c[1],g=gl,lf=glf,bbox=(ax.min()*S,ay.min()*S,(ax.max()+1)*S,(ay.max()+1)*S))
def pts(m,bb,file):
    n,L,Sh,fr,smS,smL=file
    cw=bb[2]-bb[0]; ch=bb[3]-bb[1]; mg=fr*smS
    k=min((smL-2*mg)/cw,(smS-2*mg)/ch)       # in per unit at smallest size
    return k
