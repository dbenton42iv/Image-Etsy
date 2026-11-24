import os, sys
from final import *
O='/mnt/user-data/outputs/v4'
log=[]
for m,d in DES.items():
    for key in CHOICE[m]:
        for dark,sub in ((False,'drop'),(True,'home')):
            p=f'{O}/{sub}/{d}'; os.makedirs(p,exist_ok=True)
            im,info=build_file(m,key,dark)
            fn=f'{p}/{d}_{key}.jpg'
            im.save(fn,'JPEG',quality=95,subsampling=0,dpi=(300,300),optimize=True)
            print(sub,d,key,info,flush=True)
