'''ShiCo server.

Usage:
  server.py  [-f FILES] [-n]

  -f FILES         Path to word2vec model files (glob format is supported)
                   [default: word2vecModels/195[0-1]_????.w2v]
  -n,--non-binary  w2v files are NOT binary.
'''
from docopt import docopt

from flask import Flask, jsonify
from flask_restful import reqparse
from flask.ext.cors import CORS

from vocabularymonitor import VocabularyMonitor
from vocabularyaggregator import VocabularyAggregator

from format import _yearlyNetwork

app = Flask(__name__)
CORS(app)
_vm = None


def initApp(files, binary):
    '''Initialize Flask app by loading VocabularyMonitor.

    files    Files to be loaded by VocabularyMonitor
    binary   Whether files are binary
    '''
    global _vm
    _vm = VocabularyMonitor(files, binary)

# trackClouds parameters

## VocabularyMonitor parameters:
trackParser = reqparse.RequestParser()
trackParser.add_argument('maxTerms', type=int, default=10)
trackParser.add_argument('maxRelatedTerms', type=int, default=10)
trackParser.add_argument('startKey', type=str, default=None)
trackParser.add_argument('endKey', type=str, default=None)
trackParser.add_argument('minDist', type=float, default=0.0)
trackParser.add_argument('wordBoost', type=float, default=1.0)
trackParser.add_argument('forwards', type=bool, default=True)
trackParser.add_argument('sumDistances', type=bool, default=False)
trackParser.add_argument('algorithm', type=str, default='inlinks')

## VocabularyAggregator parameters:
trackParser.add_argument('agg.weighF', type=str, default='Gaussian')
trackParser.add_argument('agg.wfParam', type=float, default=1.0)
trackParser.add_argument('agg.yearsInInterval', type=int, default=5)
trackParser.add_argument('agg.nWordsPerYear', type=int, default=10)

# Formatting functions:
# TODO: Move to module ?
# TODO: Document !
def _tuplesAsDict(pairList):
    return { word: weight for word,weight in pairList }

def _yearTuplesAsDict(results):
    return { year: _tuplesAsDict(vals) for year, vals in results.iteritems() }

def _metaToNetwork(metadata):
    return {
        "nodes": [
            { "name": "q1"},
            { "name": "q2"},
            { "name": "r1.1"},
            { "name": "r1.2"},
            { "name": "r1.3"},
            { "name": "r1.4"},
            { "name": "r2.1"},
            { "name": "r2.2"}
      ],
      "links": [
        { "source": 0, "target": 2, "value":  1 },
        { "source": 0, "target": 3, "value":  1 },
        { "source": 0, "target": 4, "value":  1 },
        { "source": 0, "target": 5, "value":  1 },
        { "source": 1, "target": 5, "value":  1 },
        { "source": 1, "target": 6, "value":  1 },
        { "source": 1, "target": 7, "value":  1 }
      ]
    }


@app.route('/track/<terms>')
def trackWord(terms):
    '''VocabularyMonitor.trackClouds service. Expects a list of terms to be
    sent to the Vocabulary monitor, and returns a JSON representation of the
    response.'''
    defaults = trackParser.parse_args()
    termList = terms.split(',')
    results,seeds, links = \
        _vm.trackClouds(termList, maxTerms=defaults['maxTerms'],
                        maxRelatedTerms=defaults['maxRelatedTerms'],
                        startKey=defaults['startKey'],
                        endKey=defaults['endKey'],
                        minDist=defaults['minDist'],
                        wordBoost=defaults['wordBoost'],
                        forwards=defaults['forwards'],
                        sumDistances=defaults['sumDistances'],
                        algorithm=defaults['algorithm'],
                        )
    agg = VocabularyAggregator(weighF=defaults['agg.weighF'],
                               wfParam=defaults['agg.wfParam'],
                               yearsInInterval=defaults['agg.yearsInInterval'],
                               nWordsPerYear=defaults['agg.nWordsPerYear']
                               )
    aggResults, aggMetadata = agg.aggregate(results)

    # TODO: use used seeds for next loop query
    networks = _yearlyNetwork(aggMetadata, aggResults, results, seeds, links)

    return jsonify(
            stream=_yearTuplesAsDict(aggResults),
            networks=networks
        )

if __name__ == '__main__':
    arguments = docopt(__doc__)
    initApp(arguments['-f'], not arguments['--non-binary'])
    app.debug = True
    app.run(host='0.0.0.0')
