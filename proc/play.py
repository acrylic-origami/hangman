import psycopg2 as pg
import json
import sys
from flask import Flask, request
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

@app.route('/poll', methods=['POST'])
def run():
	GUESS0 = [('e',0.104043615463854),
		('o',0.0793788989841674),
		('i',0.0785651421430918),
		('t',0.0781444830367422),
		('a',0.0758604871730902),
		('n',0.0705995809749965),
		('r',0.0689050328004787),
		('s',0.0659753483629688),
		('l',0.0441474876552385),
		('c',0.0380607747880563),
		('h',0.0371257410419569),
		('d',0.036390122808081),
		('u',0.0312578800795655),
		('m',0.0296884094761897),
		('f',0.0269273961211555),
		('p',0.0251145665530948),
		('g',0.0238988332499849),
		('y',0.0208894632547963),
		('w',0.0188265367636106),
		('b',0.0166917437451593),
		('v',0.0127684684189225),
		('k',0.00846655512452432),
		('x',0.00306585934076772),
		('j',0.0022877782054127),
		('q',0.00150927687721055),
		('z',0.00141051755688325)]
	with pg.connect('dbname=ng_am user=ng_am password=ng_am') as conn:
		cur = conn.cursor()
		# ls = [int(i) for i in input('Word blocks:').strip().split(',')] # (list of word lengths, e.g. `3,5,5,3` for `The quick brown fox`)
		# hits = [[] for _ in range(len(ls))]
		# fails = []
		
		body = request.form.to_dict()
		ls = json.loads(body['ls'])
		guesses = set(json.loads(body['guesses']))
		hits_flat = json.loads(body['hits'])
		hits = [{} for _ in range(len(hits_flat))]
		for hitd, subhit in zip(hits, hits_flat):
			for (pos, l) in subhit:
				if l not in hitd:
					hitd[l] = []
				hitd[l].append(pos)
				
			for v in hitd.values():
				v.sort()
				
		hitset = set(hit[1] for subhits in hits_flat for hit in subhits)
		fails = list(guesses - hitset)
		scores = []
		for l, subhits in zip(ls, hits):
			if len(subhits) == 0:
				for (guess, score) in GUESS0:
					if guess not in guesses:
						scores.append([guess, None, score])
			elif len(subhits) < l:
				# flat_hits = [s for hit in subhits for s in hit]
				# cur.execute('''
				# 	SELECT COUNT(*), SUM(score) FROM words w
				# 	LEFT JOIN letters l ON l.letter = ANY(%s) AND l.word = w.id
				# 	WHERE l.word IS NULL
				# 	''' + "".join([' AND w.l%s=%s'] * len(subhits)),
				# 	tuple([list(fails)] + flat_hits)
				# )
				# scorer = cur.fetchone()
				# num, tot = scorer
				
				# cur.execute('''
				# 	SELECT st1.letter, COUNT(*), SUM(st1.score) AS s FROM (
				# 	  SELECT l3.letter, w.score, w.id 
				# 	    FROM (SELECT * FROM words WHERE length = %s) w
				# 	    LEFT JOIN letters l2 ON w.id = l2.word AND l2.letter = ANY(%s)
				# 	    INNER JOIN letters l3 ON l3.word = w.id
				# 			WHERE l2.word IS NULL AND l3.letter <> ALL(%s)
				# 	'''\
				# 	+ "".join([' AND w.l%s=%s'] * len(subhits))\
				# 	+ ''') st1
				# 	GROUP BY st1.letter
				# 	ORDER BY s DESC''', # WHERE NOT (st1.letter ~ '[^A-Za-z]')
				# 	tuple([l, fails, list(hitset)] + flat_hits)
				# )
				
				cur.execute('''
					SELECT st1.letter, COUNT(*), SUM(st1.score) AS s FROM (
					  SELECT l0.letter, w.score, w.id 
					    FROM wordwide w
					  INNER JOIN letter_agg l0 ON l0.word = w.id
						WHERE w.length = %s AND l0.letter <> ALL(%s) AND NOT (w.wa && %s :: CHAR(1)[])
						''' + "".join([' AND w.n%s=%%s' % h[0] for h in subhits.keys()]) +
						''') st1
						GROUP BY st1.letter
						ORDER BY s DESC LIMIT 1''',
					tuple([l, list(hitset), list(fails)] + list(subhits.values()))
				)
				print(tuple([list(hitset), list(fails)] + list(subhits.values())))
				raw_scores = cur.fetchall()
				tot_score_est = sum([r[2] for r in raw_scores])
				scores += [row[:-1] + (float(row[-1]) / float(tot_score_est),) for row in raw_scores]
		
		sdict = {}
		argmax = (None, -1)
		for (letter, cnt, score) in scores:
			if letter not in sdict:
				sdict[letter] = 0
			sdict[letter] += score
			if sdict[letter] > argmax[1]:
				argmax = (letter, sdict[letter])
		return { 'next': argmax[0], 'score': str(argmax[1]) }
			
if __name__ == '__main__':
	run()