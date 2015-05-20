from os import listdir
from dcmstack import parse_and_stack

mydir = "/home/chymera/data/dc.rs/export_ME/dicom/4457/1/EPI/"

print(mydir)
filelist = listdir(mydir)
myfiles = [mydir+myfile for myfile in filelist]
results = parse_and_stack(myfiles)
print(results)
