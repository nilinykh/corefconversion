import argparse
import json
import pandas as pd
import re
from standoff2inline import Highlighter, highlight
from color_manager import ColorManager, CommonColorManager


def sort_mentions(clusters):
    res = []
    for cluster in clusters:
        cluster = sorted(cluster, key=lambda x: x[1], reverse=True)
        cluster = sorted(cluster, key=lambda x: x[0])
        res.append(cluster)
    return res


def sort_clusters(clusters):
    clusters = sorted(clusters, key=lambda x: x[0][1], reverse=True)
    clusters = sorted(clusters, key=lambda x: x[0][0])
    return clusters


def highlight_clusters(tokens, clusters, paragraphs, *, singleton_color,
        color_manager, add_indices):
    
    clusters = sort_mentions(clusters)
    clusters = sort_clusters(clusters)

    if color_manager == "complete":
        cm = ColorManager(hue_step=25, saturation_step=25, lightness_step=10)
    elif color_manager == "common":
        cm = CommonColorManager()
    else:
        cm = None

    hls = []

    if paragraphs:
        hl = Highlighter(
            prefix="<p>",
            suffix="</p>"
        )
        for start, end in paragraphs:
            hl.add_mark(start, end)
        hls.append(hl)

    counter = 1

    for i, cluster in enumerate(clusters, start=1):
        hl = None
        if len(cluster) == 1:
            if singleton_color == "":
                pass
            else:
                color = (cm.gray if cm else 'gray') \
                    if singleton_color is None else singleton_color
                start_span = f'<span style="background-color: {color};">'
                end_span = "</span>"
                hl = Highlighter(
                    prefix=f'{start_span}[{end_span}',
                    suffix=f'{start_span}]{end_span}')
        else:
            color = cm.get_next_color() if cm else "black"
            start_span = f'<span style="background-color: {color};">'
            end_span = "</span>"
            index = f"<sub>{counter}</sub>{end_span}" if add_indices else ""
            hl = Highlighter(
                prefix=f"<b>{start_span}[{end_span}",
                suffix=f"{start_span}]{index}</b>"
            )
            counter += 1
        if hl is not None: # None if only singletons, and they must not be
                           # marked, or empty document
            for start, end in cluster:
                hl.add_mark(start, end)
            hls.append(hl)

    res = highlight(tokens, *hls) 

    return res


def filter_tokens(tokens, clusters, n):
    tokens = tokens[:n]
    new_clusters = []
    for cluster in clusters:
        new_cluster = []
        for mention in cluster:
            if mention[0] < n and mention[1] < n:
                new_cluster.append(mention)
        if new_cluster:
            new_clusters.append(new_cluster)
    return tokens, new_clusters


def convert(doc, gold, n, **kwargs):
    tokens = [t for sent in doc['sentences'] for t in sent]
    if gold:
        clusters = doc.get('clusters', list())
    else:
        clusters = doc.get('predicted_clusters', doc.get('clusters', list()))
    if n:
        tokens, clusters = filter_tokens(tokens, clusters, n)
    paragraphs = doc.get('paragraphs')
    res = highlight_clusters(tokens, clusters, paragraphs, **kwargs)
    return res


def parse_args():
    # definition
    parser = argparse.ArgumentParser(prog="jsonlines2text",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("infpath", default="", help="input file")
    parser.add_argument("-o", dest="outfpath", help="output file")
    parser.add_argument("--cm", "--color-manager", dest="color_manager",
        default="complete",
        help="color manager: \"\", \"complete\" (the default), \"common\"")
    parser.add_argument("--sing-color", dest="singleton_color",
        help="singleton color: COLOR (default is 'gray') or \"\" to hide "
        "singleton markers", default=None),
    parser.add_argument("-i", "--add-indices", dest="add_indices",
        default=False, action="store_true",
        help="add indices to each chain and mention")
    parser.add_argument("-g", "--gold", dest="gold", default=False,
        action="store_true",
        help="use the 'clusters' key even if a 'predicted_clusters' key is "
        "present")
    parser.add_argument("-n", dest="n", default=0, type=int,
        help="number of tokens to consider from the beginning of the text")
    parser.add_argument("--heading", dest="heading", default="<h1>%s</h1>",
        help="template for text name, default is '<h1>%s</h1>'.  Leave "
        "blank to ignore doc name")
    parser.add_argument("--csv", dest="csv_out", help="Path to output CSV file for sentence segmentation.")
    # reading
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    sentence_list = []
    res = ""
    for line in open(args.infpath):
        doc = json.loads(line)
        doc_id = doc['doc_key']
        if args.heading:
            if "%s" in args.heading:
                res += args.heading % doc['doc_key']
            else:
                res += args.heading
        res = convert(doc, n=args.n, gold=args.gold,
            singleton_color=args.singleton_color,
            color_manager=args.color_manager, add_indices=args.add_indices
        )
        sentences = re.split(r'\s*\.\s*', res.strip())
        sentences = [sentence for sentence in sentences if sentence]

        for sentence in sentences:
            sentence_list.append((sentence, doc_id))
    df = pd.DataFrame(sentence_list, columns=['sentence', 'doc_id'])
    if args.csv_out:
        df.to_csv(args.csv_out, index=False)
    else:
        print(df)
    if args.outfpath:
        with open(args.outfpath, 'w') as f:
            f.write(res)
        

if __name__ == '__main__':
    main()
