"""Confere o contraste WCAG (mín. 4,5:1) dos pares texto/fundo dos temas escuro e claro. Uso: python3 scripts/contraste.py"""
def lum(h):
    h=h.lstrip("#"); r,g,b=(int(h[i:i+2],16)/255 for i in (0,2,4))
    f=lambda c: c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def mix(c, base, a):  # c sobre base com alfa a
    c=c.lstrip("#"); base=base.lstrip("#")
    return "#"+"".join(f"{round(int(c[i:i+2],16)*a+int(base[i:i+2],16)*(1-a)):02x}" for i in (0,2,4))
def razao(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
SOLIDOS={"verde":"#16a34a","amarelo":"#eab308","laranja":"#ea580c","vermelho":"#dc2626","azul":"#2563eb","cinza":"#94a3b8"}
TEMAS={
 "escuro":dict(fundo="#05070c",superficie="#0b1424",superficie2="#111c30",superficie3="#182640",texto="#f7f7f4",apoio="#9fb0d8",discreto="#8193b8",destaque="#6f93ff",rotulo="#75a7ff",primaria="#3a68ff",cinzaclaro="#c7d4ef",
  st=dict(verde="#4fd19b",amarelo="#f0b85a",laranja="#ff8f4d",vermelho="#ff6b78",azul="#75a7ff",cinza="#c7d4ef")),
 "claro":dict(fundo="#f4f6fb",superficie="#ffffff",superficie2="#f1f4f9",superficie3="#e5eaf3",texto="#0b0f1a",apoio="#475569",discreto="#5a6478",destaque="#1d4ed8",rotulo="#1d4ed8",primaria="#2563eb",cinzaclaro="#334155",
  st=dict(verde="#166534",amarelo="#854d0e",laranja="#9a3412",vermelho="#a61b1b",azul="#1d4ed8",cinza="#334155")),
}
pior=99
for nome,t in TEMAS.items():
    linhas=[]
    for fundo in ("fundo","superficie","superficie2","superficie3"):
        for txt in ("texto","apoio","discreto","destaque","rotulo","cinzaclaro"):
            linhas.append((f"{txt} sobre {fundo}",razao(t[txt],t[fundo])))
        for s,c in t["st"].items():
            linhas.append((f"semáforo {s} sobre {fundo}",razao(c,t[fundo])))
            sel=mix(SOLIDOS[s],t[fundo],0x1f/255)
            linhas.append((f"selo {s} (fundo tingido) sobre {fundo}",razao(c,sel)))
    linhas.append(("branco sobre botão primário",razao("#ffffff",t["primaria"])))
    m=min(linhas,key=lambda x:x[1]); falhas=[l for l in linhas if l[1]<4.5]
    print(f"{nome}: {len(linhas)} pares; menor = {m[0]} {m[1]:.2f}; abaixo de 4,5: {[(a,round(b,2)) for a,b in falhas]}")
