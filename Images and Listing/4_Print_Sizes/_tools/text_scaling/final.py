from plan import *
import pickle
CHOICE={'Bartram_Trail':{'7x5':1.4,'14x11':1.0,'20x16':1.1,'24x18':1.3,'36x24':1.0,'A1_landscape':1.2},
        'Art_Loeb_Trail':{'7x5':1.3,'14x11':1.0,'20x16':1.0,'24x18':1.1,'36x24':1.0,'A1_landscape':1.1},
        'Mountains_to_Sea_Trail':{'7x5':1.4,'14x11':1.0,'20x16':1.3,'24x18':1.4,'36x24':1.0,'A1_landscape':1.4}}
DES={'Bartram_Trail':'Bartram_Trail','Art_Loeb_Trail':'Art_Loeb_Trail','Mountains_to_Sea_Trail':'Mountains_to_Sea_Trail_Map'}
PX={'7x5':(2100,1500),'14x11':(4200,3300),'20x16':(6000,4800),'24x18':(7200,5400),'36x24':(10800,7200),'A1_landscape':(9933,7016)}
def darken(s):
    st='fill="#000000" stroke="#000000" stroke-width="{w}" stroke-linejoin="round"'
    for c,w in [('#818285',12),('#939598',8),('#a6a9ac',6)]:
        s=s.replace(f'fill="{c}" stroke="none"', st.format(w=w))
    s=s.replace('fill="#32363a" stroke="none"','fill="#000000" stroke="none"')
    s=s.replace('fill="#808285"','fill="#000000"')
    s=s.replace('fill="#d6d9da" stroke="none"','fill="#a7a9ac" stroke="none"')
    s=s.replace('fill="#000000" stroke="none"','fill="#000000" stroke="#000000" stroke-width="6" stroke-linejoin="round"')
    return s
ALIGN_RIGHT={'Art_Loeb_Trail'}   # table right edge = copyright right edge
CANDS=pickle.load(open('cands.pkl','rb'))
def build_file(m,key,dark):
    D0=dict(load(m)); D0['m']=m
    if m in ALIGN_RIGHT: D0['Rr']=CR[m][2]
    D=grow(D0); f=CHOICE[m][key]
    r=next(c for c in CANDS[m] if abs(c['f']-f)<1e-6)
    file=next(x for x in FILES if x[0]==key)
    k=pts(m,r['bbox'],file)
    fc=min(2.4,max(1.0,5.2/(48*k*72/.66)))     # copyright ~5pt at smallest size
    Rr=None
    s=svg(m,D,f,r['g'] or G,r['lf'],top=r['top'],fc=fc,cdy=r['cdy'],Rr=Rr)
    if dark: s=darken(s)
    W,H=PX[key]; mg=round(file[3]*min(W,H))
    # content bbox at fine resolution
    lo=render(s,10412/2); A=np.asarray(lo)<246; ys,xs=np.where(A)
    bb=(xs.min()*2,ys.min()*2,(xs.max()+1)*2,(ys.max()+1)*2)
    kp=min((W-2*mg)/(bb[2]-bb[0]),(H-2*mg)/(bb[3]-bb[1]))
    big=render(s,10412*kp).convert('RGB')
    art=big.crop((int(bb[0]*kp),int(bb[1]*kp),int(round(bb[2]*kp)),int(round(bb[3]*kp))))
    # tighten to exact pixels
    a=np.asarray(art.convert('L'))<246; yy,xx=np.where(a); art=art.crop((xx.min(),yy.min(),xx.max()+1,yy.max()+1))
    out=Image.new('RGB',(W,H),'white'); out.paste(art,((W-art.width)//2,(H-art.height)//2))
    return out, dict(f=f,fc=round(fc,2),table_pt=round(BASE[m][0]*f*k*72/.66,1),copy_pt=round(48*fc*k*72/.66,1),label_pt=round(BASE[m][2]*k*72/.66,1))
