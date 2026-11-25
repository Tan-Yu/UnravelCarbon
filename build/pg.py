import json,re,sys
p={x['page']:x['text'] for x in json.load(open('build/ghg-protocol-revised.plain.json'))}
for a in sys.argv[1:]:
    print(f"\n######## PDF PAGE {a}\n", re.sub(r"[ \t]*\n[ \t]*"," ",p[int(a)]))
