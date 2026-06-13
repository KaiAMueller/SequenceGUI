import json

settings_data = json.load(open("settings.json"))
cratePath = settings_data["cratePath"]
sequence_data = json.load(open(cratePath + "sequences.seq"))


for seqName, seqData in sequence_data.items():
    seqData["appearances"] = {}
for seqName, seqData in sequence_data.items():
    for segName, segData in seqData["segments"].items():
        if segData["type"] == "subsequence":
            if seqName not in sequence_data[segData["subsequence"]]["appearances"]:
                sequence_data[segData["subsequence"]]["appearances"][seqName] = [segName]
            else:
                sequence_data[segData["subsequence"]]["appearances"][seqName].append(segName)

json.dump(sequence_data, open(cratePath + "sequences.seq", "w"), indent=4)

print("done")
