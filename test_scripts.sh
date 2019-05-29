SAMRI bru2bids -o /var/tmp/samri_testing/bash/mouse -f '{"acquisition":["EPI"]}' -s '{"acquisition":["TurboRARE"]}' /usr/share/samri_bindata
SAMRI bru2bids -o /var/tmp/samri_testing/bash/rat -f '{"acquisition":["seEPI"]}' /usr/share/samri_bindata
SAMRI bru2bids -o /var/tmp/samri_testing/bash/lemur -f '{"acquisition":["geEPI"]}' -s '{"acquisition":["MSME200um"]}' /usr/share/samri_bindata
