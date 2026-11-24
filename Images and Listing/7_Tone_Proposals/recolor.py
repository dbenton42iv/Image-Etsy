import sys, re
def hx(c): c=c.lstrip('#'); return [int(c[i:i+2],16) for i in (0,2,4)]
def mix(a,b,t): return '#%02x%02x%02x'%tuple(round(x+(y-x)*t) for x,y in zip(hx(a),hx(b)))
PAL={
 'taupe_sage': dict(paper='#f5f1ea', ink='#5b4b3e', accent='#7f8c74'),
 'forest_stone': dict(paper='#f3f1ec', ink='#2e4a3b', accent='#9a8a78'),
}
src,name,out=sys.argv[1:4]; p=PAL[name]
s=open(src).read()
m={'#ffffff':p['paper'],
   '#d6d9da':mix(p['paper'],p['accent'],0.30),
   '#a6a9ac':mix(p['paper'],p['accent'],0.75),
   '#939598':p['accent'],'#818285':p['accent'],'#808285':p['accent'],
   '#32363a':mix(p['accent'],p['ink'],0.85),'#000000':p['ink']}
s=re.sub(r'fill="(#[0-9a-fA-F]{6})"',lambda g:'fill="%s"'%m.get(g.group(1).lower(),g.group(1)),s)
open(out,'w').write(s)
