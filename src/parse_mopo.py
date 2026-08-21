import re, json
from datetime import date
path = "/Users/franciscokirhman/Documents/Entrenamiento/Registro_historico_consolidado.md"
text = open(path, encoding="utf-8").read()
months = {"Jan":1,"Ene":1,"Feb":2,"Mar":3,"Apr":4,"Abr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Ago":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12,"Dic":12}
MESES_ES = {1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}
session_re = re.compile(r"^## (\d{1,2}) (\w{3}) 2026 — (.+)$", re.MULTILINE)
sessions = list(session_re.finditer(text))
results = []
for i, m in enumerate(sessions):
    day, mon, title = m.group(1), m.group(2), m.group(3).strip()
    start = m.end(); end = sessions[i+1].start() if i+1 < len(sessions) else len(text)
    block = text[start:end]; d = date(2026, months[mon], int(day))
    hora_m = re.search(r"\*\*Hora:\*\*\s*([^\n]+?)\s*(?:\s{2}|\n)", block)
    dur_m  = re.search(r"\*\*Duraci[oó]n:\*\*\s*([^\n]+?)\s*(?:\s{2}|\n)", block)
    vol_m  = re.search(r"\*\*Volumen Hevy:\*\*\s*([\d.,~]+)\s*kg", block)
    com_m  = re.search(r"\*\*Comentario:\*\*\s*([^\n]+?)\s*(?:\s{2}|\n)", block)
    rec_m  = re.search(r"\*\*R[eé]cords?:\*\*\s*([^\n]+)", block)
    rows = re.findall(r"^\|\s*[\d–\-]+\s*\|\s*(.+?)\s*\|\s*[\d–\-]+\s*\|\s*([\d.,]+|—|Peso corporal|Peso corporal \(isométrico\))\s*(?:kg)?\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|$", block, re.MULTILINE)
    results.append({"date": d.isoformat(), "dlabel": f"{int(day):02d} {MESES_ES[months[mon]]}", "title": title,
        "hora": hora_m.group(1).strip() if hora_m else None, "dur": dur_m.group(1).strip() if dur_m else None,
        "vol": vol_m.group(1).strip() if vol_m else None, "com": com_m.group(1).strip() if com_m else None,
        "rec": rec_m.group(1).strip() if rec_m else None,
        "exercises": [{"ej":e.strip(),"carga":c.strip(),"reps":r.strip(),"rpe":p.strip()} for e,c,r,p in rows]})
print(f"Total sessions: {len(results)}")
for r in results[-5:]: print(" ", r["date"], r["title"], "| vol:", r["vol"], "| filas:", len(r["exercises"]))
json.dump(results, open(f"{__import__('os').path.dirname(__file__)}/sessions_full.json","w"), ensure_ascii=False, indent=1)
