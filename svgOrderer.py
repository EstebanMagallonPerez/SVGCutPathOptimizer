import re
import math
import xml.etree.ElementTree as ET


#SVG File
INPUT_FILE = r"./WalletDoubleRoundedCorner.svg"
OUTPUT_FILE = r"./optimized.svg"

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def getNumber(value):
    if value == None:
        return None
    match = re.search(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", value)
    if match:
        return float(match.group())
    return None


def getPathPoints(d):
    if d == None:
        return None

    tokens = re.findall(r"[MmZzLlHhVvCcSsQqTtAa]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)

    x = 0
    y = 0
    startX = 0
    startY = 0
    firstPoint = None
    lastPoint = None
    command = None

    params = {
        "M":2,
        "L":2,
        "H":1,
        "V":1,
        "C":6,
        "S":4,
        "Q":4,
        "T":2,
        "A":7
    }

    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
            if command.upper() == "Z":
                x = startX
                y = startY
                lastPoint = (x,y)
                continue

        if command == None:
            i += 1
            continue

        commandType = command.upper()
        if commandType not in params:
            i += 1
            continue

        count = params[commandType]
        if i + count > len(tokens):
            break

        values = [float(tokens[i + j]) for j in range(count)]
        i += count
        relative = command.islower()

        #Move
        if commandType == "M":
            newX = values[0]
            newY = values[1]
            if relative:
                newX += x
                newY += y
            x = newX
            y = newY
            startX = x
            startY = y
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)
            command = "l" if relative else "L"

        #Line
        elif commandType == "L":
            newX = values[0]
            newY = values[1]
            if relative:
                newX += x
                newY += y
            x = newX
            y = newY
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)

        #Horizontal line
        elif commandType == "H":
            newX = values[0]
            if relative:
                newX += x
            x = newX
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)

        #Vertical line
        elif commandType == "V":
            newY = values[0]
            if relative:
                newY += y
            y = newY
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)

        #Cubic / smooth cubic
        elif commandType == "C" or commandType == "S":
            if commandType == "C":
                newX = values[4]
                newY = values[5]
            else:
                newX = values[2]
                newY = values[3]
            if relative:
                newX += x
                newY += y
            x = newX
            y = newY
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)

        #Quadratic / smooth quadratic
        elif commandType == "Q" or commandType == "T":
            if commandType == "Q":
                newX = values[2]
                newY = values[3]
            else:
                newX = values[0]
                newY = values[1]
            if relative:
                newX += x
                newY += y
            x = newX
            y = newY
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)

        #Arc
        elif commandType == "A":
            newX = values[5]
            newY = values[6]
            if relative:
                newX += x
                newY += y
            x = newX
            y = newY
            if firstPoint == None:
                firstPoint = (x,y)
            lastPoint = (x,y)

    if firstPoint == None or lastPoint == None:
        return None

    return firstPoint,lastPoint


def getElementPoints(element):
    tag = element.tag.split("}")[-1]

    if tag == "path":
        return getPathPoints(element.get("d"))

    if tag == "line":
        x1 = getNumber(element.get("x1"))
        y1 = getNumber(element.get("y1"))
        x2 = getNumber(element.get("x2"))
        y2 = getNumber(element.get("y2"))
        if None not in (x1,y1,x2,y2):
            return (x1,y1),(x2,y2)

    if tag == "polyline" or tag == "polygon":
        points = element.get("points")
        if points != None:
            values = re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",points)
            if len(values) >= 4:
                start = (float(values[0]),float(values[1]))
                end = (float(values[-2]),float(values[-1]))
                return start,end

    if tag == "rect":
        x = getNumber(element.get("x"))
        y = getNumber(element.get("y"))
        if x == None:
            x = 0
        if y == None:
            y = 0
        return (x,y),(x,y)

    if tag == "circle" or tag == "ellipse":
        x = getNumber(element.get("cx"))
        y = getNumber(element.get("cy"))
        if x != None and y != None:
            return (x,y),(x,y)

    return None


def getDistance(a,b):
    x = a[0] - b[0]
    y = a[1] - b[1]
    return math.sqrt(x * x + y * y)


def optimize(elements):
    if len(elements) == 0:
        return []

    #Start at top left
    current = min(elements,key=lambda e:(e["start"][1],e["start"][0]))
    remaining = [e for e in elements if e != current]
    result = [current]

    while len(remaining) > 0:
        closest = min(remaining,key=lambda e:getDistance(current["end"],e["start"]))
        result.append(closest)
        remaining.remove(closest)
        current = closest

    return result


def main():
    tree = ET.parse(INPUT_FILE)
    root = tree.getroot()
    elements = list(root)

    sortable = []
    unsortable = []

    #Get starting and ending points
    for element in elements:
        points = getElementPoints(element)
        if points == None:
            unsortable.append(element)
            continue
        start,end = points
        sortable.append({
            "element":element,
            "start":start,
            "end":end
        })

    print("Found",len(elements),"elements")
    print("Sortable:",len(sortable))
    print("Unsortable:",len(unsortable))

    #Optimize cut order
    ordered = optimize(sortable)

    for element in list(root):
        root.remove(element)

    for item in ordered:
        root.append(item["element"])

    #Keep unsupported elements at the end
    for element in unsortable:
        root.append(element)

    tree.write(OUTPUT_FILE,encoding="utf-8",xml_declaration=True)

    print("Saved:",OUTPUT_FILE)

    totalDistance = 0
    for i,item in enumerate(ordered):
        if i > 0:
            totalDistance += getDistance(ordered[i - 1]["end"],item["start"])
        print(i + 1,item["start"],"->",item["end"])

    print("Total travel:",totalDistance)


if __name__ == "__main__":
    main()
