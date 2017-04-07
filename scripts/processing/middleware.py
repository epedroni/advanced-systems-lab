# Handle middleware logs

import re
from numpy import mean, sqrt, square, std, percentile, histogram

lists = ["getTmw", "getTqueue", "getTserver", "setTmw", "setTqueue", "setTserver", "combinedTmw", "combinedTqueue", "combinedTserver"] 
percentiles = [0, 25, 50, 75, 95, 100]
bins = 5
scale = 1000000000
trimEdges = 0 # percentage to remove from either end of the data

# directory must be a Path object, runs is an integer, returns a list of string log paths
def getLogs(base, expdir, runs):
    return [str(base / expdir.format(run=r) / "middleware.log") for r in range(0, runs)]


# Combine multiple runs into a single set of results by stacking
def process(runs, tValue=2.776):
    results = {}
    intermediate = [read(r) for r in runs]
    
    # now we have a list of logs, stack them
    for k in lists:
        if k in intermediate[0]: results[k] = stackLists([x[k] for x in intermediate])
    
    # calculate exp finals before we overwrite the run finals
    for k in lists:
        results[k + "MeanExp"] = getMeanCI([intermediate[i][k + "Mean"] for (i, x) in enumerate(runs)], tValue)
    
    # calculate stacked finals
    calculateFinals(results)
    
    return results
    
# stack a list of lists into a single list
def stackLists(data):
    newData = []
    for d in data:
        newData = newData + d
    return newData

# Reads a specified middleware log file into an in-memory data structure
def read(log):
    results = {}
    
    # initialise fields
    for k in lists:
        results[k] = []
    results["failed"] = 0

    f = open(log, "r")
    for line in f:
        if line[0] == "#":
            next(f)

        split = line.split(",")
        if split[7].startswith("1"):
            if split[0] == "READ":
                results["getTmw"].append(max(1, int(split[2]) - int(split[1])) / scale)
                results["getTqueue"].append(max(1, int(split[4]) - int(split[3])) / scale)
                results["getTserver"].append(max(1, int(split[6]) - int(split[5])) / scale)
            elif split[0] == "WRITE":
                results["setTmw"].append(max(1, int(split[2]) - int(split[1])) / scale)
                results["setTqueue"].append(max(1, int(split[4]) - int(split[3])) / scale)
                results["setTserver"].append(max(1, int(split[6]) - int(split[5])) / scale)
            results["combinedTmw"].append(max(1, int(split[2]) - int(split[1])) / scale)
            results["combinedTqueue"].append(max(1, int(split[4]) - int(split[3])) / scale)
            results["combinedTserver"].append(max(1, int(split[6]) - int(split[5])) / scale)
        else:
            results["failed"] = results["failed"] + 1
    
    
    # remove warm up and cool down points
    if trimEdges:
        for k in lists:
            results[k] = results[k][t:-t]
            t = int(len(results[k]) * trimEdges)
    
    # calculate run finals for convenience
    calculateFinals(results)
    
    return results

# Takes a standard dictionary, adds the finals to it
def calculateFinals(results):
    for k in lists:
        results[k + "Mean"] = getMean(results[k])
        results[k + "Percentile"] = getPercentiles(results[k])
        results[k + "Distribution"] = getDistribution(results[k])

# Returns a (mean, std) tuple for a list of numbers    
def getMean(data):
    return (mean(data), std(data))

# Returns the mean and 95% confidence interval of a sample as a (mean, ci) tuple
def getMeanCI(samples, tValue):
    m = mean([x[0] for x in samples])
    ci = tValue * (std([x[1] for x in samples]) / sqrt(len(samples)))
    return (m, ci)

# Returns a list of (percentile, value) for a list of numbers
def getPercentiles(data):
    return [(p, percentile(data, p)) for p in percentiles]

# Returns a list of (bin_edge, count) for a list of numbers
def getDistribution(data):
    hist = histogram(data, bins=bins)
    
    newList = []
    for (i, x) in enumerate(hist[1][:-1]):
        newList.append((x, hist[0][i]))
    
    return newList
    
    #return [(x, hist[0][i]) for (i, x) in enumerate(hist[1][:-1])]
    
