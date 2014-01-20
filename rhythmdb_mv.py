import xml.etree.ElementTree as ET
import os, os.path, argparse, sys
import shutil
from urllib.parse import urlparse as urlparse, unquote as uridecode, quote as uriencode

class SimulationMover:
    def __init__(self):
        pass
    def rename_entry(self,old_location, new_location, entry):
        print("Moving: %s => %s" % (decoded_location, new_location))
    def move(self,old_location, new_location):
        pass

class Mover:
    def __init__(self):
        pass
    def move(self,source, dest):
        shutil.move(source, dest)
    def rename_entry(self,old_location, new_location, entry):
        entry.find("location").text = "file://" + uriencode(new_location)

def dir_basename(path):
    return os.path.basename(os.path.normpath(path))

def check_overwrite_dir(dest, sources):
    for source in sources:
        target_path = os.path.join(dest,dir_basename(source))
        if os.path.exists(target_path):
            print("Error: %s already exists in %s" % (os.path.basename(os.path.normpath(source)), dest))
            sys.exit(-1)

def check_overwrite_file(dest, sources):
    if os.path.exists(dest):
        print("Error: %s already exists" % (dest,))
        sys.exit(-1)

def check_overwrite(dest, sources):
    if os.path.isdir(dest):
        check_overwrite_dir(dest, sources)
    else:
        check_overwrite_file(dest, sources)

arg_parser = argparse.ArgumentParser(description="Move music files and update the rhythmbox db in one operation.")
arg_parser.add_argument('-t',  default=None, help="Specifies a destination directory.", metavar="dst", dest="dest_dir")
arg_parser.add_argument("--db", default=os.path.join(os.environ["HOME"], ".local/share/rhythmbox/rhythmdb.xml"), help="Specifies the location of the rhythmbox database")
arg_parser.add_argument("sources", nargs='+', help="The files to move")
arg_parser.add_argument("--force", action="store_false", dest="no_overwrite", help="Overwrite existing files or directories")
arg_parser.add_argument("--simulate", action="store_true", help="Do not actual move files or update the database, only show what would happen")

args = arg_parser.parse_args()

if not args.dest_dir and len(args.sources) < 2:
    arg_parser.print_usage()
    sys.exit(-1)

batch_mode = args.dest_dir is not None

if args.dest_dir:
    dest = args.dest_dir
    if not os.path.isdir(dest):
        print("Error: destination %s does not exist or is not a directory" % (dest,))
        sys.exit(-1)
    sources = args.sources
elif len(args.sources) > 2:
    print("dst src please")
else:
    dest = args.sources[1]
    sources = args.sources[0:1]

for source in sources:
    if not os.path.exists(source):
        print("Error: source %s does not exists" % (source,))
        sys.exit(-1)

if os.system("pgrep rhythmbox > /dev/null") == 0:
    print("You should not run this program while rhythmbox is running.")
    sys.exit(-1)

if args.no_overwrite:
    check_overwrite(dest, sources)

print("loading rhythmdb")
try:
    rdb_xml = ET.parse(args.db)
except IOError:
    print("Could not open the rhythmbox database at location %s" % (args.db))
    sys.exit(-1)

to_rename = dict([ [source, []] for source in sources ])

for entry_node in rdb_xml.getroot().findall("entry[@type='song']"):
    for source in sources:
        absolute_source = os.path.abspath(source)
        decoded_location = uridecode(urlparse(entry_node.findtext("location")).path)
        if decoded_location.startswith(absolute_source):
            to_rename[source].append((decoded_location,entry_node))
            break

if args.simulate:
    mover = SimulationMover()
else:
    mover = Mover()

absolute_dest = os.path.abspath(dest)
for (source,child_elements) in to_rename.items():
    if not child_elements:
        print("no matching entries found for %s" % (source,))
        next
    absolute_source = os.path.abspath(source)
    if not os.path.exists(absolute_dest):
        renamed_source = absolute_dest
    else:
        renamed_source = os.path.join(absolute_dest, dir_basename(absolute_source))

    try:
        mover.move(source, dest)
    except IOError as e:
        print("An error occurred copying %s to %s" % (source, dest))
        next

    for (decoded_location,entry) in child_elements:
        new_location = decoded_location.replace(absolute_source, renamed_source, 1)
        new_location = os.path.normpath(new_location)
        mover.rename_entry(decoded_location, new_location, entry)

if not args.simulate:
    rdb_xml.write(args.db, encoding="unicode")

print("complete!")
