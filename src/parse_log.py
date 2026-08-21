#!/usr/bin/env python3
"""Convierte un registro markdown (Mopo o Mipi) en JSON de sesiones.
Uso:  python3 src/parse_log.py data/Registro_historico_consolidado.md"""
import re, sys, json
from datetime import date
MESES={"Jan":1,"Ene":1,"Feb":2,"Mar":3,"Apr":4,"Abr":4,"May":5,"Jun":6,"Jul":7,
       "Aug":8,"Ago":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12,"Dic":12}
ES={1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}
FILA=re.compile(r"^\|\s*[\d–\-]+\s*\|\s*(.+?)\s*\|\s*[\d–\-]+\s*\|\s*"
                r"([\d.,]+|—|Peso corporal(?: \(isométrico\))?)\s*(?:kg)?\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|$", re.M)

def parse(path):
    t=open(path,encoding="utf-8").read()
    heads=list(re.finditer(r"^## (\d{1,2}) (\w{3}) 2026 — (.+)$", t, re.M))
    out=[]
    for i,m in enumerate(heads):
        dia,mes,titulo=m.group(1),m.group(2),m.group(3).strip()
        blq=t[m.end(): heads[i+1].start() if i+1<len(heads) else len(t)]
        d=date(2026,MESES[mes],int(dia))
        g=lambda p: (re.search(p,blq).group(1).strip() if re.search(p,blq) else None)
        out.append({"date":d.isoformat(), "dlabel":f"{int(dia):02d} {ES[MESES[mes]]}", "title":titulo,
            "hora":g(r"\*\*Hora:\*\*\s*([^\n]+?)\s*(?:\s{2}|\n)"),
            "dur": g(r"\*\*Duraci[oó]n:\*\*\s*([^\n]+?)\s*(?:\s{2}|\n)"),
            "vol": g(r"\*\*Volumen Hevy:\*\*\s*([\d.,~]+)\s*kg"),
            "com": g(r"\*\*Comentario:\*\*\s*([^\n]+?)\s*(?:\s{2}|\n)"),
            "rec": g(r"\*\*R[eé]cords?:\*\*\s*([^\n]+)"),
            "exercises":[{"ej":e.strip(),"carga":c.strip(),"reps":r.strip(),"rpe":p.strip()}
                         for e,c,r,p in FILA.findall(blq)]})
    return out

if __name__=="__main__":
    s=parse(sys.argv[1]); print(f"{len(s)} sesiones")
    for x in s[-3:]: print(" ",x["date"],x["title"],"| vol:",x["vol"],"| filas:",len(x["exercises"]))
    if len(sys.argv)>2: json.dump(s,open(sys.argv[2],"w"),ensure_ascii=False,indent=1)
