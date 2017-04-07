import memaslap, middleware
import yaml
import sys
import atexit

class Cache(object):
    def __init__(self, base, cacheFile, runs=5):
        self.base = base
        self.memaResults = None
        self.middResults = None
        self.runs = runs
        self.file = str(cacheFile)
        with open(self.file, "r") as f: self.data = yaml.load(f)
        if self.data is None: self.data = {}
        atexit.register(self.flush)

    # Get one data field, only reading it from the file if it is not already cached
    def getData(self, dirName, source, field):
        key = dirName + field
        
        if source not in self.data:
            self.data[source] = {}
        
        if key not in self.data[source]:
            if source == "memaslap":
                self.memaResults = memaslap.process([[str(l) for l in (self.base / (dirName + "-r" + str(r))).glob("mema*.log")] for r in range(0, self.runs)])
                self.data[source][key] = self.memaResults[field]
            elif source == "middleware":
                self.middResults = middleware.process([str(self.base / (dirName + "-r" + str(r)) / "middleware.log") for r in range(0, self.runs)])
                self.data[source][key] = self.middResults[field]
        
        
        return self.data[source][key]      

    # Update cache file
    def flush(self):
        with open(self.file, "w") as f: yaml.dump(self.data, stream=f)
