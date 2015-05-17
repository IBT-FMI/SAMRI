import nipype.pipeline.engine as pe
from nipype.interfaces.utility import Function
import os

data_dir = "/home/chymera/data/dc.rs/export_ME/dicom/4457/1/EPI/"
file_list = [data_dir+file for file in os.listdir(data_dir)]

imports = ["import os",
            "from dcmstack import *"
            ]

default_group_keys =  ('SeriesInstanceUID',
                       'SeriesNumber',
                       'ProtocolName',
                       'ImageOrientationPatient')

def parse_and_stack_wrapper(src_paths, group_by=default_group_keys, extractor=None, force=False, warn_on_except=False):
    from dcmstack import parse_and_stack
    return parse_and_stack(src_paths, group_by=group_by, extractor=extractor, force=force, warn_on_except=warn_on_except)


parser_stacker_function = Function(input_names=["src_paths", "group_by", "extractor", "force", "warn_on_except"],
                                    output_names=['out_file'],
                                    function=parse_and_stack_wrapper,
                                    imports=imports)

parser_stacker = pe.Node(name="parsestacker", interface=parser_stacker_function)
parser_stacker.inputs.src_paths = file_list
parser_stacker.inputs.group_by = "EchoTime"

pipeline = pe.Workflow(name='nipype_demo')
pipeline.add_nodes([parser_stacker])
pipeline.run()
pipeline.write_graph(graph2use='flat')
