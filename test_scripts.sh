pwd
ls -lah
eix samri_bindata
eix mouse-brain-atlases
SAMRI bru2bids -o . -f '{"acquisition":["EPI"]}' -s '{"acquisition":["TurboRARE"]}' /usr/share/samri_bindata
