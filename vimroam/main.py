
#BASE_DIR = vim.eval("s:plugin_path")
#sys.path.insert(0, BASE_DIR)
#from vimroam import bl

# can elect to only update backlink pages (based on modified times) when the user requests
# the backlink buffer i.e. not doing it automatically as they write to files in the wiki.
# Or you could do this, trying to always keep everything up to date at the earliest
# possible moment. Will probably stick to the former approach for now

# IMPLEMENTATION:

## starting with native Panja objects, will likely replace with tighter score Vim-roam
## objects later. Don't think it's worth trying to global these efforts despite the
## similarity between what I'll do here and with the site _beyond_ the caching system,
## which should be able to overlap fine.

## wiki.vim treats cahce as interface for getting items out of the underlying dict. That
## is, if I want a key out of the cached dict, I could call cache.get(key), instead of
## getting the raw dict first after loading the cache and then manually grabbing the key.
## Note also that the cache object only does anything when read or load is called when
## there is a noticeable change on disk (which makes sense). Otherwise in my case here
## calling load() should do nothing if we already have the current state loaded (i.e.
## start with mod_time of -1, load and change to current time. Then only reload when
## mod_time on disk is different from that stored; will always be different if not yet
## loaded).


# For now, dont need to refresh buffer on file write since changes to the file dont change
# its backlinks. However, if at some point in the future arbitrary file's backlinks can be
# loaded regardless of the current file, then we should probably just reload the buffer
# content after what we already plan to do on write (i.e. update the current file in the
# graph)

# can we just write the graph to disk on garbage collection? like how can we wait until
# the last possible moment to write

# we dont handle the case of what happens when the blbuffer's buffer actually gets
# manually destroyed. Not this will be common at all, but the object will try to open a
# window with the buffer and set a non-existent buffer number, giving "invalid range" most
# likely

import sys
import os 
import argparse
from pathlib import Path

from vimroam.cache import Cache as RoamCache
from vimroam.graph import Graph as RoamGraph
from vimroam.note  import Note  as RoamNote
from vimroam import util

# For now, can: have BLBuffer object that was be pure vimscript; run pure python calls to
# local package. for buffer just write the output from the script


def update_graph_node(note, graph, wiki_root):
    # single file update, hook to write event
    path = Path(wiki_root, note)
    name = path.stem

    if path.suffix != '.md': return False

    if name in graph.article_map:
        if path.stat().st_mtime < graph.article_map[name].ctime:
            return False

    note = RoamNote(str(path), name, verbose=False)
    if not note.valid: return False

    note.process_structure()
    graph.add_article(note)
    return True

def update_graph(graph, wiki_root, verbose=True):
    write = False
    if verbose: print('Scanning note graph...', file=sys.stdout)
    for note in util.directory_tree(wiki_root):
        if update_graph_node(note, graph, wiki_root):
            write = True
            if verbose:
                print('-> Updating {}'.format(note))
                #sys.stdout.flush()
    return write

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('wiki', help='wiki root path')
    parser.add_argument('--cache', default='~/.cache/vim-roam/', help='cache root path')
    parser.add_argument('--name', help='note name data to retrieve')
    parser.add_argument('-v', '--verbose', help='verbosity of logging', action='store_true')
    parser.add_argument('-w', '--write', help='write content output to file', action='store_true')
    parser.add_argument('--no-update', help='no update flag', action='store_true')
    args = parser.parse_args()

    notepath  = os.path.expanduser(args.wiki)
    cachepath = os.path.expanduser(args.cache)

    if args.verbose:
        print('Wiki root: {}'.format(notepath))
        print('Cache root: {}'.format(cachepath))

    roam_graph_cache = RoamCache(
        'graph',
        cachepath,
        lambda: RoamGraph()
    )

    if args.verbose: print('Loading note graph...', file=sys.stdout)
    roam_graph = roam_graph_cache.load()

    if not args.no_update:
        if update_graph(roam_graph, notepath, args.verbose):
            if args.verbose: print('Writing note graph...', file=sys.stdout)
            roam_graph_cache.write(roam_graph)

    content = ''
    if args.name:
        backlinks = roam_graph.get_backlinks(args.name)
        for srclist in backlinks.values():
            title = srclist[0]['ref'].metadata['title']

            #print('# {t} ([[{t}]])'.format(t=title))
            tstr = '# {t} ([[{t}]])'.format(t=title)
            if args.write: content += tstr+'\n'
            else: print(tstr)

            for link in srclist:
                #print(link['context'].split('\n'))
                #print(link['context'])
                cstr = link['context']
                if args.write: content += cstr+'\n'
                else: print(cstr)

    if args.write:
        with open(str(Path(cachepath, 'backlinkbuffer.1234')), 'w') as f:
            f.write(content)


