# trying to import all current samri modules
from samri import utilities
from samri.analysis import *
from samri.optimization import *
from samri.pipelines import *
# leaving out network because of graph_tool
from samri.plotting import connectivity,examples,maps,qc,summary,timeseries,utilities
from samri.report import *

def test_placeholder():
    pass
