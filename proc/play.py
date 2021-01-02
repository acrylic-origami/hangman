import psycopg2 as pg
import json
import sys
from flask import Flask, request
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

@app.route('/poll', methods=['POST'])
def run():
	GUESS0 = ['e', 'o', 'i', 'a', 'u', 'y', 's', 'p', 'm', 'c', 'd', 'b', 'j', 'l', 't', 'r', 'h', 'n', 'f', 'g', 'w', 'v', 'x', 'k', 'q', 'z']
	with pg.connect('dbname=ng_am user=ng_am password=ng_am') as conn:
		cur = conn.cursor()
		# ls = [int(i) for i in input('Word blocks:').strip().split(',')] # (list of word lengths, e.g. `3,5,5,3` for `The quick brown fox`)
		# hits = [[] for _ in range(len(ls))]
		# fails = []
		
		body = request.form.to_dict()
		ls = json.loads(body['ls'])
		guesses = json.loads(body['guesses'])
		hits = json.loads(body['hits'])
		all_hits = set(hit[1] for subhits in hits for hit in subhits)
		fails = list(set(guesses) - all_hits)
		if len(all_hits) == 0:
			return { 'next': GUESS0[len(guesses)] } # len(fails) + len(all_hits)
		else:
			scores = []
			for l, subhits in zip(ls, hits):
				if len(subhits) > 0:
					flat_hits = [s for hit in subhits for s in hit]
					# cur.execute('''
					# 	SELECT COUNT(*), SUM(score) FROM words w
					# 	LEFT JOIN letters l ON l.letter = ANY(%s) AND l.word = w.id
					# 	WHERE l.word IS NULL
					# 	''' + "".join([' AND w.l%s=%s'] * len(subhits)),
					# 	tuple([list(fails)] + flat_hits)
					# )
					# scorer = cur.fetchone()
					# num, tot = scorer
					
					cur.execute('''
						SELECT st1.letter, COUNT(*), SUM(st1.score) AS s FROM (
						  SELECT l3.letter, w.score, w.id 
						    FROM (SELECT * FROM words WHERE length = %s) w
						    LEFT JOIN letters l2 ON w.id = l2.word AND l2.letter = ANY(%s)
						    INNER JOIN letters l3 ON l3.word = w.id
								WHERE l2.word IS NULL AND l3.letter <> ALL(%s)
						'''\
						+ "".join([' AND w.l%s=%s'] * len(subhits))\
						+ ''') st1
						GROUP BY st1.letter
						ORDER BY s DESC''', # WHERE NOT (st1.letter ~ '[^A-Za-z]')
						tuple([l, fails, list(all_hits)] + flat_hits)
					)
					raw_scores = cur.fetchall()
					tot_score_est = sum([r[2] for r in raw_scores])
					scores += [row[:-1] + (row[-1] / tot_score_est,) for row in raw_scores]
			
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