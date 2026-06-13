import json

settings_data = json.load(open("settings.json"))
cratePath = settings_data["cratePath"]
sequence_data = json.load(open(cratePath + "sequences.seq"))

error_counter = 0

for seqName, seqData in sequence_data.items():
    for appSeqName in seqData["appearances"]:
        for appSegName in seqData["appearances"][appSeqName]:
            if appSegName not in sequence_data[appSeqName]["segments"] or sequence_data[appSeqName]["segments"][appSegName]["type"] != "subsequence" or sequence_data[appSeqName]["segments"][appSegName]["subsequence"] != seqName:
                print(f"{seqName} has an appearance falsely marked in {appSeqName} {appSegName}")
                error_counter += 1

for seqName, seqData in sequence_data.items():
    for segName, segData in seqData["segments"].items():
        if segData["type"] == "subsequence":
            if seqName not in sequence_data[segData["subsequence"]]["appearances"] or segName not in sequence_data[segData["subsequence"]]["appearances"][seqName]:
                print(f"{seqName} {segName} has an appearance missing in {segData['subsequence']}")
                error_counter += 1

if error_counter == 0:
    print("No errors found")
else:
    print(f"{error_counter} errors found")
    
