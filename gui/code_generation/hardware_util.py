import gui.widgets.Formula as Formula


def getZotinoStepCount(duration):
    return max(2, min(1024, int(duration / 32e-6)))


def getFastinoStepCount(duration, parallel_channels=1):
    return max(2, min(1024, int(duration / (parallel_channels * 1.5e-6))))


def getCurrentDriverStepCount(duration):
    return max(2, min(1024, int(duration / 2e-6)))


def formulaTextToDataPoints(dataLength, formula_text):
    dataX = []
    dataY = []
    for i in range(dataLength):
        x = i / (dataLength - 1)
        y = Formula.evaluate(formula_text, x)
        dataX.append(x)
        dataY.append(y)
    return dataX, dataY


def scaleFormulaData(dataX, dataY, duration, voltage, sweep_voltage):
    assert duration is not None
    minVal = min(dataY)
    maxVal = max(dataY)
    scale = (sweep_voltage - voltage) / (maxVal - minVal)
    offset = voltage - minVal * scale
    dataX_ = []
    dataY_ = []
    for i in range(len(dataX)):
        dataX_.append(dataX[i] * duration)
        dataY_.append(dataY[i] * scale + offset)
    return dataX_, dataY_

def formulaScaleFactor(dataX, dataY, duration, voltage, sweep_voltage):
    assert duration is not None
    scaleX = duration
    minVal = min(dataY)
    maxVal = max(dataY)
    scaleY = (sweep_voltage - voltage) / (maxVal - minVal)
    offsetY = voltage - minVal * scaleX
    return {"scaleX" : scaleX, "scaleY" : scaleY, "offsetY" : offsetY}

def interpolateFormulaDataToPrevious(dataX, dataY):
    dataX_ = []
    dataY_ = []
    for i in range(len(dataX) - 1):
        dataX_.append(dataX[i])
        dataY_.append(dataY[i])
        dataX_.append(dataX[i + 1])
        dataY_.append(dataY[i])
    dataX_.append(dataX[-1])
    dataY_.append(dataY[-1])
    return dataX_, dataY_
