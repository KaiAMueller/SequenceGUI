def setIndexOfKeyInDict(d: dict, movingKey: str, newIndex: int) -> dict:
    if movingKey not in d:
        return d
    newDict = {}
    indexCounter = 0
    for key in d:
        if indexCounter == newIndex:
            newDict[movingKey] = d[movingKey]
        if key != movingKey:
            indexCounter += 1
            newDict[key] = d[key]
    if indexCounter == newIndex:
        newDict[movingKey] = d[movingKey]
    return newDict


def getUniqueKey(d: dict, name: str = "") -> str:
    i = 0
    while True:
        key = str(name) + str(i)
        if key not in d:
            return key
        i += 1


def unitValueToText(value: dict) -> str:
    return f"{value['text']} {value['unit']['text']}"


def textToIdentifier(text: str) -> str:
    if text == "" or text is None:
        return text
    text = "".join([c if (c.isidentifier() or c.isdigit()) else "_" for c in text])
    return "_" + text if text[0].isdigit() else text


def int_range_reader(value: int, min: int, max: int) -> int:
    if int(value) < min or int(value) > max:
        raise ValueError(f"Value {value} is not in range [{min}, {max}]")
    return value
